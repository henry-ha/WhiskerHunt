"""v1.0 cover-photo replacement, original-photo preservation, native failure rollback."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(rgb):
 im=Image.new('RGB',(110,95),rgb);buf=io.BytesIO();im.save(buf,format='JPEG')
 return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()

async def pending(page):
 await page.wait_for_function('nativeSyncPending.size===1',timeout=5000)
 return await page.evaluate('Array.from(nativeSyncPending.keys())[0]')

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
  await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
  await page.evaluate('''() => {window.openDb=async()=>({});window.transact=async(store,mode,method)=>method==='getAll'?[]:undefined;boot()}''')
  await page.wait_for_function('window.whiskerBootComplete')
  first,second,third=photo((155,91,50)),photo((78,130,158)),photo((110,65,148))
  cat={'id':'cat1','name':'Pudding','coat':'Tabby','personality':'Curious','note':'Original',
       'photo':first,'signature':'first-signature','visualHash':None,'createdAt':'2026-10-13T10:00:00Z','fav':False,
       'sightings':[{'id':'s1','at':'2026-10-13T10:00:00Z','photo':None,'signature':'first-signature','note':'First encounter'},
                    {'id':'s2','at':'2026-10-14T10:00:00Z','photo':second,'signature':'second-signature','note':'Return'},
                    {'id':'s3','at':'2026-10-15T10:00:00Z','photo':third,'signature':'third-signature','note':'Another return'}]}
  payload={'app':'Whisker Hunt','version':1,'cats':[cat],'profile':{'name':'Explorer','xp':240,'claimed':[]}}
  await page.evaluate('''d=>{window.whiskerNativeReady=true;window.whiskerRequestNativeSync=t=>window.__lastToken=t;
    window.whiskerUseNativeStorage(JSON.stringify(d));}''',payload)
  await page.evaluate('openDetail("cat1")')
  assert await page.locator('[data-cover-sighting]').count()==2
  # Successful save: original first sighting gains an explicit photo, XP/IDs untouched.
  await page.locator('[data-cover-sighting="s2"]').click()
  token=await pending(page)
  state=await page.evaluate('backupPayload()')
  c=state['cats'][0]
  assert c['photo']==second and c['sightings'][0]['photo']==first and c['signature']=='second-signature'
  assert [x['id'] for x in c['sightings']]==['s1','s2','s3'] and state['profile']['xp']==240
  await page.evaluate('(t)=>window.whiskerNativeSyncResult(t,true)',token)
  await page.wait_for_function('s.busy===false')
  assert await page.locator('[data-cover-sighting="s2"]').is_disabled()
  assert await page.locator('[data-cover-sighting="s1"]').count()==1
  await page.screenshot(path=str(ROOT/'tests/v10-cover-action.png'))
  # A second cover change fails; restore cover, signature and hash without losing the first photo.
  await page.locator('[data-cover-sighting="s3"]').click()
  token=await pending(page)
  await page.evaluate('(t)=>window.whiskerNativeSyncResult(t,false)',token)
  await page.wait_for_function('s.busy===false')
  state=await page.evaluate('backupPayload()');c=state['cats'][0]
  assert c['photo']==second and c['sightings'][0]['photo']==first and c['signature']=='second-signature'
  assert state['profile']['xp']==240
  # Existing v1 backup remains valid; no new schema keys needed.
  assert state['version']==1 and len(c['sightings'])==3
  assert not errors,errors
  cs=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
  assert 'sightingIds' in cs and 'xp.TryGetDouble' in cs
  assert "const CACHE='whisker-hunt-shell-v19'" in (ROOT/'BrowserPreview/sw.js').read_text()
  print('PASSED v1.0: cover selection, first-photo retention, native ACK rollback, XP/IDs/schema unchanged, cache version')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
