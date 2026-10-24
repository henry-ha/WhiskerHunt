"""Hush Hunt 3.10.1 camera entry / zoom UI browser regression. Fake Chromium camera, not Android hardware."""
import asyncio,threading
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from playwright.async_api import async_playwright
R=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
async def main():
 pth=R/'BrowserPreview';raw=R/'WhiskerHunt/Resources/Raw';csproj=(R/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert '<ApplicationVersion>64</ApplicationVersion>' in csproj
 assert '<ApplicationDisplayVersion>3.10.1</ApplicationDisplayVersion>' in csproj
 assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in csproj
 assert 'index_v64.html' in (R/'WhiskerHunt/MainPage.xaml').read_text()
 for fn in ('app_v64.js','style_v64.css','sw.js'):
  assert (pth/fn).read_bytes()==(raw/fn).read_bytes(),fn
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda exc:errors.append(str(exc)))
  import re
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',(pth/'index.html').read_text())
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(pth/'style_v64.css').read_text())
  await page.add_script_tag(content=(pth/'app_v64.js').read_text())
  await page.evaluate("""()=>{
   Object.defineProperty(window,'isSecureContext',{value:true,configurable:true});
   const cam=document.createElement('canvas');cam.width=640;cam.height=480;
   const ctx=cam.getContext('2d');ctx.fillStyle='#40a070';ctx.fillRect(0,0,640,480);
   const stream=cam.captureStream(24);
   Object.defineProperty(navigator,'mediaDevices',{value:{
    enumerateDevices:async()=>[{deviceId:'test-standard',kind:'videoinput',label:'Back Camera'}],
    getUserMedia:async()=>stream
   },configurable:true});
   window.__cats=new Map();window.__meta=new Map();
   window.openDb=async()=>({mock:true,transaction:()=>{const tx={objectStore:store=>({put:value=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value)}})};setTimeout(()=>tx.oncomplete?.(),0);return tx}});
   window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return [...m.values()];if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}};
   boot();
  }""")
  await page.wait_for_function('window.whiskerBootComplete===true')
  assert await page.locator('#hush-direct-live').count()==1
  assert await page.locator('#hush-direct-ar').count()==1
  assert await page.locator('.hush-direct-btn').count()==2
  await page.screenshot(path=str(R/'HushHunt_v3.10.1_Home_Preview.png'))
  await page.locator('#hush-direct-live').click()
  await page.wait_for_selector('#encounter-stage.live-encounter',timeout=15000)
  assert await page.locator('#hush-quick-shutter').is_visible()
  assert await page.locator('#hush-live-zoom').is_visible()
  assert 'contain'==await page.locator('#encounter-video').evaluate('el=>getComputedStyle(el).objectFit')
  assert await page.locator('#hush-live-zoom').inner_text()
  assert await page.locator('#modal-layer .capture-choice').count()==0,'extra capture mode chooser opened'
  await page.locator('#hush-quick-shutter').click()
  await page.wait_for_selector('#wildlife-species',timeout=15000)
  assert await page.locator('#save-catch').count()==1
  assert await page.evaluate('s.cats.length')==0,'quick shutter must not auto-save'
  await page.locator('#modal-layer [data-close]').click()
  assert await page.evaluate('liveCamera===null')
  await page.locator('#hush-direct-ar').click()
  assert await page.get_by_text('ARCore • Real surfaces').count()==1
  assert await page.get_by_text('2D Safari • Quick play').count()==1
  assert await page.evaluate('s.cats.length')==0
  assert not errors,errors
  await browser.close()
 print('PASS v3.10.1: direct home choices, no intermediate live chooser, real camera preview, uncropped image, quick shutter to original save form, AR chooser, data untouched')
if __name__=='__main__':asyncio.run(main())
