"""Hush Hunt v3.8.6 compatibility wildlife change, species Bingo, AR wildlife, optional OSM tiles, distances, data-safety."""
import asyncio,base64,io,re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
 im=Image.new('RGB',(320,420),(123,151,169));b=io.BytesIO();im.save(b,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
async def main():
 pth=ROOT/'BrowserPreview';native=ROOT/'WhiskerHunt/Resources/Raw'
 assert '<ApplicationVersion>50</ApplicationVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert 'window.whiskerNativeBridge=true;' in (native/'index_v50.html').read_text()
 assert (native/'app_v50.js').read_bytes()==(pth/'app_v50.js').read_bytes()
 assert (native/'style_v50.css').read_bytes()==(pth/'style_v50.css').read_bytes()
 assert 'android.permission.INTERNET' in (ROOT/'WhiskerHunt/Platforms/Android/AndroidManifest.xml').read_text()
 from PIL import ImageStat
 red=Image.open(pth/'field_art/ant-red-ant.webp').convert('RGB');yellow=Image.open(pth/'field_art/ant-yellow-meadow-ant.webp').convert('RGB');black=Image.open(pth/'field_art/ant-black-garden-ant.webp').convert('RGB')
 assert red.getpixel((81,75))[0]>red.getpixel((81,75))[1]
 assert yellow.getpixel((81,75))[0]>yellow.getpixel((81,75))[2]
 assert black.getpixel((81,75))[0]<100
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
  errors=[];requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url) if 'tile.openstreetmap.org' in r.url else None)
  await page.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','', (pth/'index.html').read_text())
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html);await page.add_style_tag(content=(pth/'style_v50.css').read_text());await page.add_script_tag(content=(pth/'app_v50.js').read_text())
  photos={f.name:'data:image/webp;base64,'+base64.b64encode(f.read_bytes()).decode() for f in (pth/'field_art').glob('*.webp')}
  await page.evaluate('''pictures=>{window.fieldGuideArt=(group,type)=>{const x=v=>String(v).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');return pictures[x(group)+'-'+(type?x(type):'group')+'.webp']||''}}''', photos)
  await page.evaluate('''()=>{window.__cats=new Map();window.__meta=new Map();window.openDb=async()=>({mock:true,transaction:()=>{const tx={objectStore:store=>({put:value=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value)}})};setTimeout(()=>tx.oncomplete?.(),0);return tx}});window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return [...m.values()];if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}};boot()}''')
  await page.wait_for_function('window.whiskerBootComplete===true')
  assert await page.evaluate('HUSH_AR_CATALOG.length')>=85
  assert await page.evaluate('new Set(AR_CAT_MODELS.map(m=>m.species||"Cat")).size')==17
  assert await page.evaluate('FIELD_TOOLS.Rabbit.primary')=='Carrot Token'
  assert await page.evaluate('FIELD_TOOLS.Butterfly.primary')=='Photo Net'
  # Live selector: tool swap without camera restart or discarding an encounter.
  await page.evaluate('''im=>{s.wildTarget='Snail';s.encounterAr=false;s.encounterLive=true;s.realLiveProof={source:'camera-stream',images:new Set([im]),ready:false};s.image=im;showEncounter(im,{score:12,label:'Live',note:''},{live:true})}''',photo())
  assert await page.locator('#encounter-species').count()==1
  await page.locator('#encounter-species').select_option('Butterfly')
  assert await page.locator('#throw-item .hush-photo-net-svg').count()==1
  assert 'Photo Net' in await page.locator('.encounter-quick-help').inner_text()
  await page.locator('#encounter-species').select_option('Rabbit')
  assert await page.locator('#throw-item .wild-tool-art').inner_text()=='🥕'
  assert await page.evaluate('s.encounterLive===true && s.wildTarget==="Rabbit"')
  await page.screenshot(path=str(ROOT/'HushHunt_v3.8.4_LiveTools_Preview.png'))
  await page.evaluate('closeModal()')
  # all-group Bingo, with cats still retaining original coat bonus game.
  await page.evaluate('''im=>{s.cats=[{id:'old-cat',name:'Mochi',coat:'Tabby',species:'Cat',photo:im,createdAt:new Date().toISOString(),sightings:[{id:'visit-cat',at:new Date().toISOString(),lat:51.50,lng:-.12}]},{id:'snail-1',name:'Shelly',species:'Snail',speciesDetail:'Garden Snail',coat:'Other',photo:im,createdAt:new Date().toISOString(),sightings:[{id:'visit-snail',at:new Date().toISOString(),lat:51.53,lng:-.11}]}];navigate('dex')}''',photo())
  assert await page.locator('.hush-challenge-tile').count()==17
  assert '2 / 17' in await page.locator('.hush-challenge').inner_text()
  assert await page.locator('.bingo').count()==1
  await page.locator('[data-hush-filter="Species:Snail"]').click()
  assert await page.evaluate('s.filter')=='Species:Snail'
  assert await page.locator('.variant-album').count()==1
  await page.screenshot(path=str(ROOT/'HushHunt_v3.8.4_Bingo_Preview.png'))
  # Private plot requests no OSM tile until explicit opt-in.
  await page.evaluate("navigate('explore')")
  assert await page.locator('#hush-street-toggle').count()==1
  assert len(requests)==0
  await page.locator('#hush-street-toggle').click()
  assert 'IP address' in await page.locator('#modal-layer').inner_text()
  assert len(requests)==0
  await page.locator('#hush-map-accept').click()
  await page.wait_for_selector('#hush-street-map')
  assert len(requests)>0
  assert await page.locator('.hush-street-pin').count()==2
  assert 'mi straight-line' in await page.locator('#hush-map-distances').inner_text()
  await page.screenshot(path=str(ROOT/'HushHunt_v3.8.4_StreetMap_Preview.png'))
  await page.locator('#hush-zoom-in').click()
  assert await page.evaluate('s.hushStreetZoom')==15
  await page.locator('#hush-street-toggle').click()
  assert not await page.locator('#hush-street-map').count()
  assert await page.evaluate('s.hushStreetEnabled===false')
  # Virtual Safari discovery: non-cat model, sprite, save, backup; original cat untouched.
  await page.evaluate('''im=>{s.arModelKey=HUSH_AR_CATALOG.find(m=>m.species==='Snail').key;s.arHabitatKey=AR_HABITATS[0].key;s.encounterAr=true;s.encounterCaptured=true;s.encounterFocus={x:.5,y:.6};s.image=im;showVirtualNamingForm()}''',photo())
  assert 'SNAIL NAME' in await page.locator('label[for=virtual-name]').inner_text()
  await page.locator('#virtual-save-final').click()
  await page.wait_for_function('s.cats.some(c=>c.virtual&&c.species==="Snail")',timeout=10000)
  assert await page.evaluate('s.cats.filter(c=>!c.virtual).length')==2
  backup=await page.evaluate('backupPayload()')
  assert {c.get('species') for c in backup['cats']}=={'Cat','Snail'}
  assert any(c.get('virtual') is True and c.get('species')=='Snail' for c in backup['cats'])
  await page.evaluate("navigate('dex')")
  assert 'My AR wildlife' in await page.locator('.virtual-gallery').inner_text()
  assert not errors,errors
  print('PASS v3.8.4: 17-group Bingo, live species tools, recoloured ants, opt-in OSM, distance calculations, virtual snail saved, v1 backups, private storage')
  await browser.close()
if __name__=='__main__':asyncio.run(main())
