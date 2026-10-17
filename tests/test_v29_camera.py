"""AR Safari v2.9 live MediaStream performance + no background frame sampling."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
  html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
  await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
  await page.evaluate('''() => {
   window.__cats=new Map();window.__meta=new Map();
   window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value);}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
   window.transact=async (store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete'){m.delete(value);return}};
   Object.defineProperty(window,'isSecureContext',{configurable:true,value:true});
   const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;
   const ctx=canvas.getContext('2d');ctx.fillStyle='#73919c';ctx.fillRect(0,0,640,480);
   ctx.fillStyle='#bb9f8b';ctx.fillRect(0,210,640,270);
   window.__cameraCanvas=canvas;window.__cameraStream=canvas.captureStream(25);
   Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>window.__cameraStream}});
   boot();
  }''')
  await page.wait_for_function('window.whiskerBootComplete===true')
  await page.locator('#hero-catch').click()
  await page.locator('#ar-photo').click()
  await page.locator('.encounter-stage.live-encounter').wait_for(timeout=12000)
  assert await page.locator('.ar-model-target').count()==1
  assert await page.evaluate('s.encounterAr&&liveCamera?.active')
  assert await page.evaluate('liveCamera.frames.length')==0
  await page.wait_for_timeout(1300)
  assert await page.evaluate('liveCamera.frames.length')==0,'AR mode should not continuously sample JPEGs'
  assert await page.locator('.ar-model-target.ar-autospawn').count()==1
  await page.screenshot(path=str(ROOT/'WhiskerHunt_v2.9_AutoSpawn_Preview.png'),full_page=False)
  await page.evaluate('handleEncounterHit("ball",.2)')
  await page.wait_for_function('liveCamera===null',timeout=10000)
  await page.locator('#encounter-continue').wait_for(state='visible')
  assert await page.evaluate('window.__cameraStream.getVideoTracks()[0].readyState')=='ended'
  assert await page.evaluate('s.cats.length')==0
  assert not errors,errors
  print('PASS v2.9 live camera: virtual cat auto-spawns, no background JPEG processing, camera stops after catch')
  await browser.close()
if __name__=='__main__':asyncio.run(main())
