"""v3.8.5 regression: Android/native ARCore source integration and WebView result handoff.
No Android build or physical world tracking is claimed by this browser/mock test."""
from pathlib import Path
import asyncio,base64,re
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
async def main():
 native=ROOT/'WhiskerHunt';source=(native/'Platforms/Android/HushArCoreActivity.cs').read_text(); bridge=(native/'MainPage.xaml.cs').read_text()
 assert 'XPACE.Google.ARCore' in (native/'WhiskerHunt.csproj').read_text()
 assert 'android.hardware.camera.ar' in (native/'Platforms/Android/AndroidManifest.xml').read_text()
 assert 'android:value="optional"' in (native/'Platforms/Android/AndroidManifest.xml').read_text()
 assert 'Session(this)' in source and 'frame.HitTest(' in source and 'hit.CreateAnchor()' in source
 assert 'anchor.Pose.GetTranslation(' in source and 'camera.GetViewMatrix' in source and 'camera.GetProjectionMatrix' in source
 assert 'GlReadPixels' in source and 'GrabFrame' in source
 assert 'case "arcore"' in bridge and 'OnArCoreCompleted' in bridge
 assert 'uk.whiskerhunt.mobile' in (native/'WhiskerHunt.csproj').read_text()
 assert 'whisker-hunt-state.json' in bridge and 'app.GetString() != "Whisker Hunt"' in bridge
 assert (native/'Resources/Raw/app_v49.js').read_bytes()==(ROOT/'BrowserPreview/app_v49.js').read_bytes()
 assert (native/'Resources/Raw/style_v49.css').read_bytes()==(ROOT/'BrowserPreview/style_v49.css').read_bytes()
 assert 'window.whiskerNativeBridge=true;' in (native/'Resources/Raw/index_v49.html').read_text()
 assert '<ApplicationVersion>49</ApplicationVersion>' in (native/'WhiskerHunt.csproj').read_text()
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
  base=ROOT/'BrowserPreview'
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',(base/'index.html').read_text());html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(base/'style_v49.css').read_text())
  await page.add_script_tag(content=(base/'app_v49.js').read_text())
  await page.evaluate('''()=>{window.openDb=async()=>({mock:true,transaction:()=>{let tx={objectStore:()=>({put:()=>null})};setTimeout(()=>tx.oncomplete?.(),0);return tx}});window.transact=async()=>[];boot()}''')
  await page.wait_for_function('window.whiskerBootComplete===true')
  # Browser shows 2D fallback and disables native-only option.
  await page.evaluate('startArEncounter()')
  assert await page.locator('#hush-arcore-start').is_disabled()
  assert await page.locator('#hush-ar-2d').count()==1
  await page.evaluate('closeModal()')
  # Mock native shell (without navigating the WebView to a custom URI).
  await page.evaluate('''()=>{window.whiskerNativeReady=true;window.whiskerNativeBridge=true;hushChooseArSafari()}''')
  assert await page.locator('#hush-arcore-start').is_enabled()
  text=await page.locator('#modal-layer').inner_text();assert 'Google Play Services for AR' in text
  await page.evaluate('closeModal()')
  fake='data:image/jpeg;base64,'+base64.b64encode(b'\xff\xd8\xff\xd9').decode()
  await page.evaluate('''photo=>{window.persistCatchAtomic=async()=>true;s.db={mock:true};s.cats=[];window.hushNativeArCoreResult({status:'captured',model:'wildlife-snail-garden-snail',photo})}''',fake)
  assert await page.locator('#virtual-photo-preview').count()==1
  assert await page.locator('#virtual-save-final').count()==1
  assert 'ARCore' in await page.locator('#modal-layer').inner_text()
  assert await page.evaluate('s.encounterCaptured&&s.encounterAr&&s.image===s.hushNativeArPhoto')
  await page.locator('#virtual-save-final').click()
  await page.wait_for_function('s.cats.length===1')
  assert await page.evaluate('s.cats[0].virtual===true&&s.cats[0].species==="Snail"&&s.cats[0].photo===s.hushNativeArPhoto')
  assert await page.evaluate('s.cats[0].sightings[0].captureMode') == 'ar-virtual'
  assert not errors,errors
  await browser.close()
 print('PASS v3.8.5: native ARCore wiring, optional manifest, anchored placement code, photo callback, 2D fallback, virtual-only save, unchanged package/storage')
if __name__=='__main__':asyncio.run(main())
