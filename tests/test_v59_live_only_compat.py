"""v3.9.5: real wildlife catches require verified live-camera frame, while old data remains restorable."""
import asyncio,base64,io,re
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(rgb):
 im=Image.new('RGB',(300,360),rgb)
 d=ImageDraw.Draw(im);d.ellipse((45,40,235,315),outline=(241,243,240),width=12)
 out=io.BytesIO();im.save(out,format='JPEG')
 return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
 assert 'Source="index_v59.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
 cs=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert '<ApplicationDisplayVersion>3.9.5</ApplicationDisplayVersion>' in cs and '<ApplicationVersion>59</ApplicationVersion>' in cs
 src=(ROOT/'BrowserPreview/app_v59.js').read_text()
 assert src==(ROOT/'WhiskerHunt/Resources/Raw/app_v59.js').read_text()
 assert (ROOT/'BrowserPreview/style_v59.css').read_text()==(ROOT/'WhiskerHunt/Resources/Raw/style_v59.css').read_text()
 assert 'window.whiskerNativeBridge=true;' in (ROOT/'WhiskerHunt/Resources/Raw/index_v59.html').read_text()
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'BrowserPreview/index.html').read_text()
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style_v59.css').read_text())
  await page.add_script_tag(content=src)
  legacy=photo((185,157,104)); snail=photo((95,135,79));dog=photo((76,115,150)); gallery=photo((95,55,70))
  await page.evaluate('''image=>{
    window.__cats=new Map();window.__meta=new Map();
    window.openDb=async()=>({mock:true,transaction:()=>{const tx={objectStore:store=>({put:value=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value)}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
    window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return [...m.values()];if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete')m.delete(value)};
    window.__cats.set('legacycat01',{id:'legacycat01',name:'Older Kitty',coat:'Tabby',personality:'Sleepy',note:'Old photo remains.',photo:image,signature:'legacy',createdAt:new Date().toISOString(),sightings:[{id:'legacysighting01',at:new Date().toISOString(),note:'Imported before live-only',lat:51.52,lng:-.12,photo:null}]});
    boot();
  }''',legacy)
  await page.wait_for_function('window.whiskerBootComplete===true')
  assert await page.evaluate('s.cats.length')==1
  await page.evaluate('startCatch()')
  assert await page.locator('#live-photo').count()==1
  assert await page.locator('#ar-photo').count()==1
  assert await page.locator('#pick-photo').count()==0
  assert await page.locator('#take-photo').count()==0
  # Import callback shouldn't open a collectible form.
  await page.evaluate('img=>beginEncounter(img,{live:false})',gallery)
  assert await page.locator('#wildlife-species').count()==0
  assert await page.locator('#live-only-retry').count()==1
  assert await page.evaluate('s.cats.length')==1
  # Simulate a camera-session start and finish using actual candidate frames;
  # the code under test must not accept a fake gallery photo later.
  async def simulated_live(image):
   await page.evaluate('''img=>{
     const video=document.createElement('video');
     liveCamera={active:true,stream:{getTracks:()=>[]},video,frames:[{image:img,quality:null,at:Date.now()}],timer:null,sampling:false,dragging:false};
     s.encounterAr=false;
     beginEncounter(img,{live:true});
   }''',image)
   await page.wait_for_selector('#encounter-stage')
   await page.evaluate('async()=>{await freezeLiveEncounter()}')
   await page.wait_for_function('s.realLiveProof?.ready===true')
   assert await page.locator('#encounter-replace').count()==0
   assert await page.locator('#encounter-retake').inner_text()=='🎥 Retake live'
  await simulated_live(snail)
  # A late gallery response replacing the chosen frame must be rejected.
  await page.evaluate('img=>{s.image=img;showCatForm(img)}',gallery)
  assert await page.locator('#wildlife-species').count()==0
  assert await page.evaluate('s.cats.length')==1
  await simulated_live(snail)
  await page.evaluate('()=>showCatForm(s.image)')
  await page.wait_for_selector('#wildlife-species')
  assert 'Live camera discovery' in await page.locator('.live-only-verified').inner_text()
  await page.locator('#wildlife-species').select_option('Snail')
  await page.locator('#cat-name').fill('Shelly')
  await page.locator('#field-guide-custom').click()
  await page.locator('#wildlife-detail').fill('Garden snail')
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.wait_for_function('s.cats.length===2')
  details=await page.evaluate('''()=>({snail:s.cats.find(c=>c.name==='Shelly'), legacy:s.cats.find(c=>c.name==='Older Kitty')})''')
  assert details['snail']['species']=='Snail'
  assert details['snail']['sightings'][0]['captureMode']=='live'
  assert details['legacy']['photo']==legacy
  # After saved cat, no old session can be reused for new catch.
  assert not await page.evaluate('realLivePhotoReady()')
  await page.evaluate('startCatch()')
  assert not await page.evaluate('realLivePhotoReady()')
  # Add a second species from another simulated live session and preserve backups.
  await simulated_live(dog)
  await page.evaluate('()=>showCatForm(s.image)')
  await page.locator('#wildlife-species').select_option('Dog')
  await page.locator('#cat-name').fill('Buddy')
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.wait_for_function('s.cats.length===3')
  payload=await page.evaluate('backupPayload()')
  assert payload['version']==1
  assert len(payload['cats'])==3
  assert {'Snail','Dog'}.issubset({c.get('species') for c in payload['cats']})
  await page.evaluate('''async payload=>{window.confirm=()=>true;s.cats=[];await loadBackupText(JSON.stringify(payload))}''',payload)
  assert await page.evaluate('s.cats.length')==3
  await page.evaluate('startCatch()')
  await page.locator('#live-photo').click()
  assert await page.locator('#live-normal-gallery').count()==0
  assert await page.locator('#live-normal-camera').count()==0
  assert not errors,errors
  print('PASSED v3.9.5: live-only new real sightings, no gallery/normal-camera fallback, snail/dog saving, old photos and backup compatibility')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
