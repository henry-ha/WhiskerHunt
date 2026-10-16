"""v0.8 Android WebView bridge contract tests in Chromium (native callback simulated)."""
import asyncio,base64,io,json
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
 im=Image.new('RGB',(96,96),(212,120,90));b=io.BytesIO();im.save(b,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()

async def wait_pending(page):
 await page.wait_for_function('nativeSyncPending.size===1',timeout=8000)
 return await page.evaluate('Array.from(nativeSyncPending.keys())[0]')

async def ack(page,ok):
 token=await wait_pending(page)
 await page.evaluate('([token,ok])=>window.whiskerNativeSyncResult(token,ok)',[token,ok])

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
  cat={'id':'test-cat','name':'Miso','coat':'Ginger','personality':'Friendly','note':'',
       'photo':photo(),'signature':'test','createdAt':'2026-10-13T11:00:00Z','fav':False,
       'sightings':[{'id':'first','at':'2026-10-13T11:00:00Z','note':'hello','photo':None,'lat':51.5,'lng':-0.1}]}
  payload={'app':'Whisker Hunt','version':1,'cats':[cat],'profile':{'name':'Explorer','xp':125,'claimed':[]}}
  await page.evaluate('''(data)=>{window.whiskerNativeReady=true;window.confirm=()=>true;window.whiskerRequestNativeSync=token=>{window.__lastToken=token};window.whiskerUseNativeStorage(JSON.stringify(data));}''',payload)
  assert await page.evaluate('s.cats.length')==1
  # ACK is not instantaneous: the promise stays pending until native confirms.
  promise=asyncio.create_task(page.evaluate('nativeSync().then(()=>"saved",()=>"failed")'))
  await ack(page,True)
  assert await promise=='saved'
  # A failed Android write rejects, rather than displaying false success.
  promise=asyncio.create_task(page.evaluate('nativeSync().then(()=>"saved",()=>"failed")'))
  await ack(page,False)
  assert await promise=='failed'
  # Cat deletion snapshots the *updated* collection; a failure restores it.
  await page.evaluate('navigate("dex")')
  await page.locator('.cat-tile').first.click()
  await page.locator('#delete-cat').click()
  await page.locator('#confirm-delete').click()
  token=await wait_pending(page)
  assert await page.evaluate('backupPayload().cats.length')==0
  await page.evaluate('(t)=>window.whiskerNativeSyncResult(t,false)',token)
  await page.wait_for_function('s.busy===false')
  assert await page.evaluate('s.cats.length')==1
  await page.locator('#confirm-delete').click()
  token=await wait_pending(page)
  assert await page.evaluate('backupPayload().cats.length')==0
  await page.evaluate('(t)=>window.whiskerNativeSyncResult(t,true)',token)
  await page.wait_for_function('s.busy===false')
  assert await page.evaluate('s.cats.length')==0
  # Native mode never borrows IndexedDB cats if native file is missing.
  await page.evaluate('''() => {s.cats=[{id:'phantom'}];window.whiskerUseNativeStorage(null)}''')
  assert await page.evaluate('s.cats.length')==0
  assert await page.evaluate('s.profile.xp')==0
  # Privacy pin removal waits for a durable write; rollback on rejection.
  await page.evaluate('''(data)=>window.whiskerUseNativeStorage(JSON.stringify(data))''',payload)
  await page.evaluate('openPrivacyTools()')
  await page.locator('#forget-all-pins').click()
  token=await wait_pending(page)
  assert await page.evaluate('pinnedSightings()')==0
  await page.evaluate('(t)=>window.whiskerNativeSyncResult(t,false)',token)
  await page.wait_for_function('s.busy===false')
  assert await page.evaluate('pinnedSightings()')==1
  assert await page.evaluate('s.profile.xp')==125
  # C# source must include ACK callback and correctly identify PNG/WebP.
  cs=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
  assert 'window.whiskerNativeSyncResult(' in cs and 'var token = GetQuery(request, "request")' in cs
  assert '"image/png"' in cs and '"image/webp"' in cs
  assert not errors,errors
  print('PASSED v0.8: native ACK success/failure, deletion rollback + snapshot order, privacy rollback, native empty-state isolation, image MIME bridge')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
