"""v1.1: idempotent quest claims, chronological XP cooldown, read-only collection audit."""
import asyncio,base64,io
from datetime import datetime,timedelta,timezone
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
  now=datetime.now(timezone.utc)
  recent=(now-timedelta(minutes=10)).isoformat();old=(now-timedelta(hours=2)).isoformat()
  cat={'id':'cat1','name':'Miso','coat':'Ginger','personality':'Friendly','note':'',
       'photo':photo((175,120,80)),'signature':'original','createdAt':recent,'fav':False,
       'sightings':[{'id':'recent','at':recent,'note':'hello','photo':None,'signature':'original'},
                    {'id':'older','at':old,'note':'earlier','photo':photo((140,95,45)),'signature':'older'}]}
  payload={'app':'Whisker Hunt','version':1,'cats':[cat],'profile':{'name':'Explorer','xp':200,'claimed':[]}}
  await page.evaluate('''d=>{window.whiskerNativeReady=true;window.confirm=()=>true;
    window.whiskerRequestNativeSync=t=>window.__lastToken=t;
    window.whiskerUseNativeStorage(JSON.stringify(d));}''',payload)
  # Quest is eligible, but two taps during a native write must award only once.
  await page.evaluate('navigate("quests")')
  await page.locator('[data-claim="first"]').click()
  token=await pending(page)
  await page.evaluate('claimQuest("first")')
  assert await page.evaluate('s.profile.xp')==235
  assert await page.evaluate('s.profile.claimed.length')==1
  await page.evaluate('(t)=>window.whiskerNativeSyncResult(t,true)',token)
  await page.wait_for_function('s.busy===false')
  assert await page.evaluate('s.profile.xp')==235
  # A failed claim must restore XP and marker, allowing retry.
  await page.locator('[data-claim="double"]').click()
  token=await pending(page)
  await page.evaluate('(t)=>window.whiskerNativeSyncResult(t,false)',token)
  await page.wait_for_function('s.busy===false')
  assert await page.evaluate('s.profile.xp')==235
  assert await page.evaluate('s.profile.claimed.length')==1
  await page.locator('[data-claim="double"]').click()
  token=await pending(page)
  await page.evaluate('(t)=>window.whiskerNativeSyncResult(t,true)',token)
  await page.wait_for_function('s.busy===false')
  assert await page.evaluate('s.profile.xp')==295
  # Read-only audit must not alter the collection or private pins.
  before=await page.evaluate('JSON.stringify({cats:s.cats,profile:s.profile})')
  await page.evaluate('openPrivacyTools()')
  await page.locator('#check-health').click()
  assert await page.get_by_text('No structural problems found').is_visible()
  assert await page.evaluate('JSON.stringify({cats:s.cats,profile:s.profile})')==before
  await page.locator('#health-back').click()
  assert await page.locator('#export-safe').count()==1
  # Return-sighting cooldown: final array item is old, but a recent item exists.
  repeat=photo((70,145,185))
  await page.evaluate('im=>{window.locationPrompt=async()=>null;showCatForm(im);document.getElementById("mode-repeat").click();document.getElementById("real-cat").checked=true;}',repeat)
  await page.locator('#save-catch').click()
  token=await pending(page)
  assert await page.evaluate('s.profile.xp')==295, 'Cooldown must not award XP for recent return'
  assert await page.evaluate('s.cats[0].sightings.length')==3
  await page.evaluate('(t)=>window.whiskerNativeSyncResult(t,true)',token)
  await page.wait_for_function('s.busy===false')
  assert await page.evaluate('s.profile.xp')==295
  assert await page.evaluate('s.cats[0].sightings.length')==3
  assert not errors,errors
  js=(ROOT/'BrowserPreview/app.js').read_text();native=(ROOT/'WhiskerHunt/Resources/Raw/app.js').read_text()
  assert js==native
  assert "const CACHE='whisker-hunt-shell-v22'" in (ROOT/'BrowserPreview/sw.js').read_text()
  print('PASSED v1.1: quest double-tap lock, failed claim rollback/retry, read-only audit, unordered-sighting cooldown, unchanged backup schema, asset sync')
  await browser.close()
if __name__=='__main__':asyncio.run(main())
