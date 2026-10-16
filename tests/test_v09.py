"""v0.9 native boot handshake and corrupt snapshot recovery; Chromium bridge simulation."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
 im=Image.new('RGB',(90,90),(182,127,87));b=io.BytesIO();im.save(b,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'WhiskerHunt/Resources/Raw/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
  await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
  await page.evaluate('''() => {window.__readyRequests=0;window.whiskerRequestNativeReady=()=>window.__readyRequests++;
   window.openDb=()=>{throw Error('IndexedDB must never open in Android shell')};window.confirm=()=>true;
   window.whiskerRequestNativeSync=t=>window.__lastToken=t;boot()}''')
  await page.wait_for_function('window.whiskerBootComplete')
  assert await page.evaluate('window.__readyRequests')==1
  assert await page.evaluate('s.native && s.db===null && !window.whiskerNativeReady')
  assert await page.get_by_text('Loading your CatDex…').is_visible()
  await page.locator('#nav-catch').click()
  assert await page.evaluate('s.db===null && s.cats.length===0')
  # Normal first boot loads a prior collection only after the ready handshake.
  cat={'id':'cat1','name':'Pudding','coat':'Tabby','photo':photo(),'createdAt':'2026-10-13T12:00:00Z',
       'sightings':[{'id':'spot1','at':'2026-10-13T12:00:00Z','note':'Hello','photo':None}], 'signature':'test','fav':False}
  payload={'app':'Whisker Hunt','version':1,'cats':[cat],'profile':{'name':'Explorer','xp':210,'claimed':[]}}
  await page.evaluate('(d)=>window.whiskerUseNativeStorage(JSON.stringify(d))',payload)
  assert await page.evaluate('s.cats.length===1 && s.profile.xp===210 && s.db.native && !s.storageBlocked')
  assert await page.get_by_text('Pudding').is_visible()
  # Invalid native snapshots must block ordinary writes, including empty collection overwrites.
  await page.evaluate("window.whiskerNativeStorageError('Unreadable primary and backup')")
  assert await page.evaluate('s.storageBlocked && s.cats.length===0')
  assert await page.get_by_text('Collection needs recovery').is_visible()
  assert await page.evaluate('nativeSync().then(()=>"saved",()=>"blocked")')=='blocked'
  await page.locator('#retry-native').click()
  assert await page.evaluate('window.__readyRequests')==2
  await page.evaluate("window.whiskerNativeStorageError('Still unreadable')")
  # Explicitly confirmed import is permitted to replace an unreadable snapshot.
  pending=asyncio.create_task(page.evaluate('''async (d)=>{
    await loadBackupText(JSON.stringify(d));return {cats:s.cats.length,xp:s.profile.xp,blocked:s.storageBlocked};
  }''',payload))
  await page.wait_for_function('window.__lastToken!==undefined',timeout=5000)
  token=await page.evaluate('window.__lastToken')
  assert await page.evaluate('s.recoveryApproved && s.storageBlocked')
  await page.evaluate('(t)=>window.whiskerNativeSyncResult(t,true)',token)
  result=await pending
  assert result=={'cats':1,'xp':210,'blocked':False},result
  assert not errors,errors
  # Confirm native and browser entry points differ without changing storage schema.
  browser_html=(ROOT/'BrowserPreview/index.html').read_text()
  assert 'whiskerAndroidShell' not in browser_html
  cs=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
  xaml=(ROOT/'WhiskerHunt/MainPage.xaml').read_text()
  assert 'case "ready": await LoadNativeStateAsync();' in cs
  assert 'Navigated="OnWebNavigated"' not in xaml
  assert 'hadSnapshots && previous is null' in cs
  assert '_stateRecoveryBlocked && !allowRecovery' in cs
  assert 'GetQuery(request, "recover") == "1"' in cs
  assert 'if (_stateRecoveryBlocked)' in cs
  print('PASSED v0.9: Android handshake, no IndexedDB on native, load gating, corrupt save protection, retry, explicit restore, browser/native separation')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
