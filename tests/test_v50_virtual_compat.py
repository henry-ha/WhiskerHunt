"""AR Safari retains virtual-cat saving without creating fake real-wildlife records."""
import asyncio,base64,io,re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
def photo():
 im=Image.new('RGB',(320,420),(133,157,170));b=io.BytesIO();im.save(b,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
async def run():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'BrowserPreview/index.html').read_text()
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style_v50.css').read_text())
  await page.add_script_tag(content=(ROOT/'BrowserPreview/app_v50.js').read_text())
  await page.evaluate('''()=>{
    window.__cats=new Map();window.__meta=new Map();
    window.openDb=async()=>({mock:true,transaction:()=>{const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value)}})};setTimeout(()=>tx.oncomplete?.(),0);return tx}});
    window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return [...m.values()];if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}};
    boot();
  }''')
  await page.wait_for_function('window.whiskerBootComplete===true')
  await page.evaluate('''(img)=>{s.arModelKey=AR_CAT_MODELS[5].key;s.arHabitatKey=AR_HABITATS[4].key;s.encounterAr=true;s.encounterCaptured=true;s.encounterFocus={x:.5,y:.6};s.image=img;showVirtualNamingForm()}''',photo())
  await page.wait_for_selector('#virtual-save-final')
  assert not await page.evaluate('realLivePhotoReady()')
  await page.locator('#virtual-save-final').click()
  await page.wait_for_function('s.cats.length===1')
  cat=await page.evaluate('s.cats[0]')
  assert cat['virtual'] is True and cat['sightings'][0]['captureMode']=='ar-virtual'
  assert await page.evaluate('visibleWildlife().length')==0
  assert await page.evaluate('backupPayload().cats[0].virtual') is True
  assert not errors, errors
  print('PASSED: virtual AR cat gameplay and backup unaffected by real-wildlife live-only gate')
  await browser.close()
if __name__=='__main__':asyncio.run(run())
