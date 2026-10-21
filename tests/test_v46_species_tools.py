"""v3.8.2: provisional Faunigo label, species-specific live tools, and old CatDex compatibility."""
import asyncio,base64,io,re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def img(rgb):
 image=Image.new('RGB',(320,400),rgb)
 buffer=io.BytesIO();image.save(buffer,format='JPEG',quality=82)
 return 'data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode()

async def main():
 proj=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert '<ApplicationTitle>Faunigo</ApplicationTitle>' in proj
 assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in proj
 assert '<ApplicationDisplayVersion>3.8.2</ApplicationDisplayVersion>' in proj
 assert '<ApplicationVersion>46</ApplicationVersion>' in proj
 assert 'Source="index_v46.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
 assert 'window.whiskerNativeBridge=true;' in (ROOT/'WhiskerHunt/Resources/Raw/index_v46.html').read_text()
 assert (ROOT/'BrowserPreview/app_v46.js').read_bytes()==(ROOT/'WhiskerHunt/Resources/Raw/app_v46.js').read_bytes()
 assert (ROOT/'BrowserPreview/style_v46.css').read_bytes()==(ROOT/'WhiskerHunt/Resources/Raw/style_v46.css').read_bytes()
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'BrowserPreview/index.html').read_text()
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style_v46.css').read_text())
  await page.add_script_tag(content=(ROOT/'BrowserPreview/app_v46.js').read_text())
  legacy=img((176,129,78));snail=img((116,157,82))
  await page.evaluate('''image=>{
   window.__cats=new Map();window.__meta=new Map();
   window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{const tx={objectStore:store=>({put:value=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value);}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
   window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return [...m.values()];if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value;}if(method==='delete')m.delete(value)};
   window.__cats.set('legacycat1',{id:'legacycat1',name:'Mochi',coat:'Tabby',personality:'Sleepy',note:'Old cat',photo:image,signature:'legacy',createdAt:new Date().toISOString(),sightings:[{id:'legacyvisit1',at:new Date().toISOString(),note:'Old photo',lat:null,lng:null,photo:null}]});
   boot();
  }''',legacy)
  await page.wait_for_function('window.whiskerBootComplete===true')
  assert 'faunigo' in (await page.locator('.brand').inner_text()).lower()
  assert await page.evaluate('s.cats.length')==1
  await page.evaluate('startCatch()')
  assert await page.locator('#wild-target').count()==1
  assert await page.locator('#pick-photo').count()==0
  assert await page.locator('#take-photo').count()==0
  assert await page.locator('#wild-target').input_value()=='Unknown'
  await page.locator('#wild-target').select_option('Snail')
  assert await page.evaluate('s.wildTarget')=='Snail'
  await page.evaluate('''image=>{const video=document.createElement('video');liveCamera={active:true,stream:{getTracks:()=>[]},video,frames:[{image,quality:null,at:Date.now()}],timer:null,sampling:false,dragging:false};s.encounterAr=false;beginEncounter(image,{live:true})}''',snail)
  await page.wait_for_selector('#encounter-stage')
  assert await page.locator('#throw-item .wild-tool-art').inner_text()=='🍃'
  assert 'Leaf Stamp' in await page.locator('.encounter-quick-help').inner_text()
  assert await page.locator('#tool-ball').is_hidden()
  assert 'Macro Lens' in await page.locator('#tool-lure').get_attribute('aria-label')
  await page.locator('#tool-lure').click()
  assert await page.locator('#throw-item .wild-tool-art').inner_text()=='🔎'
  await page.evaluate('handleEncounterHit("lure",.3)')
  assert await page.locator('#throw-item .wild-tool-art').inner_text()=='🍃'
  assert 'Focused!' in await page.locator('#encounter-status').inner_text()
  await page.evaluate('async()=>{await freezeLiveEncounter()}')
  await page.wait_for_function('s.realLiveProof?.ready===true')
  await page.evaluate('showCatForm(s.image)')
  assert await page.locator('#wildlife-species').input_value()=='Snail'
  await page.locator('#cat-name').fill('Shelly')
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.wait_for_function('s.cats.length===2')
  payload=await page.evaluate('backupPayload()')
  assert payload['version']==1
  assert {x.get('species','Cat') for x in payload['cats']}=={'Cat','Snail'}
  await page.evaluate('''async payload=>{window.confirm=()=>true;s.cats=[];await loadBackupText(JSON.stringify(payload))}''',payload)
  assert await page.evaluate('s.cats.length')==2
  await page.evaluate('startCatch()')
  await page.locator('#wild-target').select_option('Cat')
  await page.evaluate('''image=>{const video=document.createElement('video');liveCamera={active:true,stream:{getTracks:()=>[]},video,frames:[{image,quality:null,at:Date.now()}],timer:null,sampling:false,dragging:false};s.encounterAr=false;beginEncounter(image,{live:true})}''',legacy)
  await page.wait_for_selector('#encounter-stage')
  assert await page.locator('#throw-item svg.whisker-paw-svg').count()==1
  assert 'Dangle Lure' in await page.locator('#tool-lure').get_attribute('aria-label')
  assert not errors,errors
  print('PASS v3.8.2: snail Leaf Stamp/Macro Lens, cat Claw/Lure, strict live-only, backup and legacy cats')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
