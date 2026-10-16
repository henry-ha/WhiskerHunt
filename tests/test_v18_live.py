"""v1.8 in-browser camera test using a real canvas MediaStream.
The browser sandbox blocks localhost navigation, so canvas.captureStream()
provides actual decoded video frames without accessing physical camera hardware.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
  await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
  await page.evaluate('''() => {
    window.__cats=new Map();window.__meta=new Map();
    window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value);}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
    window.transact=async (store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete'){m.delete(value);return}};
    // Simulated live camera: real MediaStream frames from an animated canvas.
    Object.defineProperty(window,'isSecureContext',{configurable:true,value:true});
    const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;
    const ctx=canvas.getContext('2d');let frame=0;
    window.__cameraDraw=setInterval(()=>{frame++;ctx.fillStyle=frame%2?'#8792af':'#7789a5';ctx.fillRect(0,0,640,480);ctx.fillStyle='#f3d2a8';ctx.beginPath();ctx.ellipse(280,200,140,120,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='#12131d';ctx.fillRect(235,185,12,12);ctx.fillRect(325,185,12,12);},40);
    window.__cameraCanvas=canvas;window.__cameraStream=canvas.captureStream(25);
    Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>window.__cameraStream}});
    boot();
  }''')
  await page.wait_for_function('window.whiskerBootComplete===true')
  await page.locator('#hero-catch').click()
  await page.locator('#live-photo').click()
  await page.locator('#encounter-video').wait_for(timeout=12000)
  await page.wait_for_function('liveCamera && liveCamera.frames.length >= 2',timeout=12000)
  assert await page.evaluate('liveCamera.video.videoWidth>0 && liveCamera.video.videoHeight>0')
  assert await page.locator('.encounter-tool-dock').count()==1
  assert await page.locator('.encounter-stage.live-encounter').count()==1
  assert await page.locator('#live-frame-count').count()==1
  assert await page.evaluate('liveCamera.frames.length<=8')
  await page.wait_for_timeout(3200)
  assert await page.evaluate('liveCamera.frames.length<=8')
  assert await page.evaluate('liveCamera.frames.at(-1).at-liveCamera.frames[0].at<=3000')
  assert await page.evaluate('''() => chooseBestLiveFrame([
   {image:'dark',quality:{score:75,brightness:20}},
   {image:'clear',quality:{score:60,brightness:130}}
  ]).image''')=='clear'
  await page.screenshot(path=str(ROOT/'tests/v18-live-camera.png'),full_page=True)
  async def throw():
   a=await page.locator('#throw-item').bounding_box();b=await page.locator('#encounter-cat').bounding_box()
   start=(a['x']+a['width']/2,a['y']+a['height']/2);end=(b['x']+b['width']/2,b['y']+b['height']/2)
   await page.mouse.move(*start);await page.mouse.down();await page.mouse.move(*end,steps=12)
   assert await page.locator('#encounter-aim-guide').evaluate('(e)=>e.classList.contains("aim-hit")')
   await page.mouse.up()
  await page.locator('#tool-lure').click();await throw()
  assert await page.evaluate('s.encounterLured')
  assert await page.evaluate('s.encounterTool')=='ball'
  await throw()
  await page.wait_for_function('s.encounterCaptured && liveCamera===null',timeout=12000)
  assert await page.locator('#encounter-video').count()==0
  assert await page.evaluate('s.image.startsWith("data:image/jpeg;base64,")')
  assert await page.evaluate('s.captureSummary.quality.width>0')
  assert await page.evaluate('window.__cameraStream.getVideoTracks()[0].readyState')=='ended'
  assert await page.locator('#encounter-quality').get_by_text('Best of',exact=False).count()==1
  assert await page.evaluate('s.cats.length')==0
  await page.locator('#encounter-continue').wait_for();await page.locator('#encounter-continue').click()
  await page.locator('#cat-name').fill('Livecat');await page.locator('#real-cat').check();await page.locator('#save-catch').click()
  await page.get_by_text('Livecat',exact=True).first.wait_for()
  assert await page.evaluate('s.cats.length')==1
  assert await page.evaluate('s.cats[0].sightings.length')==1
  assert await page.evaluate('s.cats[0].photo.startsWith("data:image/jpeg;base64,")')
  assert await page.evaluate('s.profile.xp')>=100
  await page.locator('#nav-catch').click()
  # The test stream was stopped after capture; supply a new real MediaStream.
  await page.evaluate('''() => {window.__cameraStream=window.__cameraCanvas.captureStream(25)}''')
  # Use a fresh canvas with a live track, rather than relying on a stopped stream.
  await page.locator('#live-photo').click()
  await page.locator('#encounter-video').wait_for(timeout=12000)
  # Retake invokes a picker. Before the picker opens, a still must be frozen so
  # cancellation leaves a visible photo and the capture interaction intact.
  async with page.expect_file_chooser() as chooser_info:
   await page.locator('#encounter-retake').click()
  chooser=await chooser_info.value
  assert chooser is not None
  assert await page.evaluate('liveCamera===null')
  assert await page.locator('#encounter-video').count()==0
  assert await page.locator('#encounter-photo').is_visible()
  assert await page.evaluate('s.image.startsWith("data:image/jpeg;base64,")')
  await page.locator('[data-close]').first.click()
  assert await page.evaluate('s.cats.length')==1
  # Closing an active preview stops all tracks without changing the CatDex.
  await page.locator('#nav-catch').click()
  await page.evaluate('''() => {window.__cameraStream=window.__cameraCanvas.captureStream(25)}''')
  await page.locator('#live-photo').click()
  await page.locator('#encounter-video').wait_for(timeout=12000)
  await page.locator('[data-close]').first.click()
  assert await page.evaluate('liveCamera===null')
  assert await page.evaluate('window.__cameraStream.getVideoTracks()[0].readyState')=='ended'
  assert await page.evaluate('s.cats.length')==1
  await page.locator('#nav-catch').click()
  await page.evaluate('''() => {navigator.mediaDevices.getUserMedia=async()=>{throw Error("Camera disabled in test")};}''')
  await page.locator('#live-photo').click()
  await page.get_by_role('heading',name='Live camera unavailable').wait_for(timeout=12000)
  assert await page.locator('#live-normal-camera').count()==1
  assert await page.locator('#live-normal-gallery').count()==1
  assert not errors,errors
  # Static native bridge wiring checks; NOT a substitute for an Android build.
  native=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
  chrome=(ROOT/'WhiskerHunt/Platforms/Android/WhiskerWebChromeClient.cs').read_text()
  maui=(ROOT/'WhiskerHunt/MauiProgram.cs').read_text()
  assert 'case "camera-permission"' in native
  assert 'request.Grant(new[] { PermissionRequest.ResourceVideoCapture })' in chrome
  assert 'request.Deny()' in chrome and 'CheckSelfPermission' in chrome
  assert 'SetWebChromeClient(new WhiskerWebChromeClient(handler))' in maui
  await page.evaluate('clearInterval(window.__cameraDraw)')
  print('PASS v1.8: actual canvas MediaStream, rolling frames, lure + drag, best-frame freeze, CatDex save, camera fallback')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
