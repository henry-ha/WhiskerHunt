"""Hush Hunt v3.9.0: unit preferences, remembered online-map consent, and species-appropriate AR Safari.
Browser simulation only; device compilation and native ARCore tracking not verified.
"""
import asyncio,base64,io,re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
 im=Image.new('RGB',(350,420),(73,122,155));out=io.BytesIO();im.save(out,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()
async def main():
 pth=ROOT/'BrowserPreview';raw=ROOT/'WhiskerHunt/Resources/Raw';csproj=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert '<ApplicationVersion>54</ApplicationVersion>' in csproj
 assert '<ApplicationDisplayVersion>3.9.0</ApplicationDisplayVersion>' in csproj
 assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in csproj
 assert 'window.whiskerNativeBridge=true;' in (raw/'index_v54.html').read_text()
 assert (raw/'app_v54.js').read_bytes()==(pth/'app_v54.js').read_bytes()
 assert (raw/'style_v54.css').read_bytes()==(pth/'style_v54.css').read_bytes()
 assert 'index_v54.html' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
  errors=[];map_requests=[]
  page.on('pageerror',lambda err:errors.append(str(err)))
  page.on('request',lambda r:map_requests.append(r.url) if 'tile.openstreetmap.org' in r.url else None)
  await page.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','', (pth/'index.html').read_text())
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(pth/'style_v54.css').read_text())
  await page.add_script_tag(content=(pth/'app_v54.js').read_text())
  await page.evaluate('''()=>{window.__cats=new Map();window.__meta=new Map();window.openDb=async()=>({mock:true,transaction:()=>{const tx={objectStore:store=>({put:value=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value)}})};setTimeout(()=>tx.oncomplete?.(),0);return tx}});window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return [...m.values()];if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}};boot()}''')
  await page.wait_for_function('window.whiskerBootComplete===true')
  assert await page.evaluate('hushViewSettings().units')=='imperial'
  assert await page.evaluate('hushViewSettings().streetMapEnabled') is False
  await page.evaluate("navigate('profile')")
  assert await page.locator('#hush-unit-setting').input_value()=='imperial'
  assert not await page.locator('#hush-street-setting').is_checked()
  await page.locator('#hush-unit-setting').select_option('metric')
  await page.wait_for_function('s.profile.viewSettings?.units==="metric" && window.__meta.get("profile")?.value?.viewSettings?.units==="metric"')
  assert '700 m' in await page.evaluate('hushDistanceText(.7)')
  await page.locator('#hush-unit-setting').select_option('imperial')
  await page.wait_for_function('s.profile.viewSettings?.units==="imperial" && window.__meta.get("profile")?.value?.viewSettings?.units==="imperial"')
  assert 'mi straight-line' in await page.evaluate('hushDistanceText(.7)')
  assert 'yd straight-line' in await page.evaluate('hushDistanceText(.2)')
  # The profile toggle must ask permission; no tiles before that.
  await page.locator('#hush-street-setting').click()
  assert await page.locator('#modal-layer').is_visible()
  assert await page.locator('#hush-street-setting').is_checked() is False
  assert len(map_requests)==0
  await page.locator('#hush-map-cancel').click()
  assert await page.evaluate('s.profile.viewSettings.streetMapEnabled') is False
  # Add sample pinned points; testing data is mocked, not tied to anyone's location.
  im=photo()
  await page.evaluate('''im=>{s.cats=[{id:'cat-old',name:'Kitty',species:'Cat',coat:'Tabby',photo:im,createdAt:'2026-09-30T11:00:00Z',sightings:[{id:'s-cat',at:'2026-09-30T11:00:00Z',lat:51.5,lng:-.12}]},{id:'snail-old',name:'Shelly',species:'Snail',speciesDetail:'Garden Snail',coat:'Other',photo:im,createdAt:'2026-09-30T11:00:00Z',sightings:[{id:'s-snail',at:'2026-09-30T11:00:00Z',lat:51.51,lng:-.11}]}]}''', im)
  await page.evaluate("navigate('explore')")
  assert len(map_requests)==0
  await page.locator('#hush-street-toggle').click()
  assert len(map_requests)==0
  await page.locator('#hush-map-accept').click()
  await page.wait_for_function('s.profile.viewSettings?.streetMapEnabled===true && window.__meta.get("profile")?.value?.viewSettings?.streetMapEnabled===true')
  await page.wait_for_selector('#hush-street-map')
  assert len(map_requests)>0
  assert 'mi straight-line' in await page.locator('#hush-map-distances').inner_text()
  await page.screenshot(path=str(ROOT/'HushHunt_v3.9.0_Map_Preview.png'))
  # A cold native-state load respects preferences: only the existing profile extension differs.
  serialized=await page.evaluate('JSON.stringify(backupPayload())')
  await page.evaluate('snapshot=>window.whiskerUseNativeStorage(snapshot)',serialized)
  assert await page.evaluate('s.profile.viewSettings.units')=='imperial'
  assert await page.evaluate('s.profile.viewSettings.streetMapEnabled') is True
  await page.evaluate("navigate('explore')")
  assert await page.locator('#hush-street-map').count()==1
  # Simulate native profile sync ack so we can switch OFF and verify persistence.
  await page.evaluate('''()=>{window.whiskerRequestNativeSync=token=>setTimeout(()=>window.whiskerNativeSyncResult(token,true),0)}''')
  await page.locator('#hush-street-toggle').click()
  await page.wait_for_function('s.profile.viewSettings.streetMapEnabled===false')
  await page.wait_for_selector('#hush-street-map',state='detached')
  assert await page.locator('#hush-street-map').count()==0
  # Native reload again from current state must default back to offline plot.
  await page.evaluate('window.whiskerUseNativeStorage(JSON.stringify(backupPayload()))')
  await page.evaluate("navigate('explore')")
  assert await page.locator('#hush-street-map').count()==0
  await page.evaluate("navigate('profile')")
  assert await page.locator('#hush-unit-setting').input_value()=='imperial'
  assert not await page.locator('#hush-street-setting').is_checked()
  await page.screenshot(path=str(ROOT/'HushHunt_v3.9.0_Profile_Preview.png'))
  # Serve bundled artwork inline for a faithful visual preview without local-file HTTP access.
  pictures={f.name:'data:image/webp;base64,'+base64.b64encode(f.read_bytes()).decode() for f in (pth/'field_art').glob('*.webp')}
  await page.evaluate('''pictures=>{window.fieldGuideArt=(group,type)=>{const x=v=>String(v).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');return pictures[x(group)+'-'+(type?x(type):'group')+'.webp']||''}}''',pictures)
  # 2D Safari: hedgehog must have leaf token in both draggable item and captured orb.
  await page.evaluate('''im=>{s.arModelKey=HUSH_AR_CATALOG.find(m=>m.species==='Hedgehog').key;s.arHabitatKey=AR_HABITATS[0].key;s.encounterAr=true;s.encounterCaptured=false;s.image=im;showEncounter(im,{label:'Live',score:0,note:''},{ar:true})}''',im)
  assert 'Leaf Badge' in await page.locator('.encounter-quick-help').inner_text()
  assert '🍂' in await page.locator('#throw-item').inner_text()
  assert '🍂' in await page.locator('#encounter-orb').inner_text()
  assert 'hedgehog' in (await page.locator('#encounter-continue').inner_text()).lower()
  assert 'virtual varieties' in await page.locator('.ar-smart-note').inner_text()
  assert 'cats' not in (await page.locator('.ar-smart-note').inner_text()).lower()
  assert 'Binoculars' in await page.locator('#tool-lure').inner_text()
  # Alternate tool should switch icon and back correctly.
  await page.locator('#tool-lure').click()
  assert '🔭' in await page.locator('#throw-item').inner_text()
  await page.locator('#tool-ball').click()
  assert '🍂' in await page.locator('#throw-item').inner_text()
  await page.evaluate('handleEncounterHit("ball",.25)')
  await page.wait_for_timeout(1300)
  assert '🍂' in await page.locator('#encounter-orb').inner_text()
  assert not await page.locator('#encounter-continue').is_hidden()
  await page.screenshot(path=str(ROOT/'HushHunt_v3.9.0_Hedgehog_Preview.png'))
  await page.locator('#encounter-continue').click()
  assert 'hedgehog' in (await page.locator('#virtual-save-final').inner_text()).lower()
  assert 'hedgehog' in (await page.locator('label[for=virtual-name]').inner_text()).lower()
  # Regression of another group with a unique shaped tool.
  await page.evaluate('''im=>{s.arModelKey=HUSH_AR_CATALOG.find(m=>m.species==='Butterfly').key;s.encounterAr=true;s.encounterCaptured=false;s.image=im;showEncounter(im,{label:'Live',score:0,note:''},{ar:true})}''',im)
  assert await page.locator('#throw-item .hush-photo-net-svg').count()==1
  assert await page.locator('#encounter-orb .hush-photo-net-svg').count()==1
  assert 'Photo Net' in await page.locator('.encounter-quick-help').inner_text()
  # Cat retains the whisker paw and its own language.
  await page.evaluate('''im=>{s.arModelKey=AR_CAT_MODELS.find(m=>!m.species).key;s.encounterAr=true;s.encounterCaptured=false;s.image=im;showEncounter(im,{label:'Live',score:0,note:''},{ar:true})}''',im)
  assert await page.locator('#throw-item .whisker-paw-svg').count()==1
  assert await page.locator('#encounter-orb .whisker-paw-svg').count()==1
  assert not errors,errors
  await browser.close()
 print('PASS v3.9.0: imperial/metric, persistent map consent on simulated native restart, no tiles before opt-in, hedgehog/Butterfly/Cat Safari tools & labels, collection untouched')
if __name__=='__main__':asyncio.run(main())
