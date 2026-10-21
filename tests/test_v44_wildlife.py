"""v3.8.0 FieldDex integration tests including old backup import and real photo saves."""
import asyncio,base64,io,re,json
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
def picture(color=(142,116,91)):
 im=Image.new('RGB',(360,270),color); d=ImageDraw.Draw(im);d.ellipse((20,20,220,230),outline=(255-color[0],255-color[1],255-color[2]),width=11);d.rectangle((240,185,340,268),fill=(color[2],color[0],color[1]));buf=io.BytesIO();im.save(buf,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()
async def run():
 assert 'index_v44.html' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
 project=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text();assert '<ApplicationDisplayVersion>3.8.0</ApplicationDisplayVersion>' in project and '<ApplicationVersion>44</ApplicationVersion>' in project
 raw=ROOT/'WhiskerHunt/Resources/Raw';js=(ROOT/'BrowserPreview/app.js').read_text()
 assert js==(raw/'app_v44.js').read_text()
 assert (ROOT/'BrowserPreview/style.css').read_text()==(raw/'style_v44.css').read_text()
 assert 'window.whiskerNativeBridge=true;' in (raw/'index_v44.html').read_text()
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':400,'height':850})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'BrowserPreview/index.html').read_text();html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html);html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text());await page.add_script_tag(content=js)
  old=picture((187,151,123))
  await page.evaluate('''img=>{
   window.__cats=new Map();window.__meta=new Map();
   window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{
    const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value);}})};
    setTimeout(()=>tx.oncomplete?.(),0);return tx;
   }});
   window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete'){m.delete(value);return}}
   const legacy={id:'originalcat01',name:'Mochi',coat:'Tabby',personality:'Sleepy',note:'An older cat.',photo:img,signature:'legacy-signature',createdAt:new Date().toISOString(),sightings:[{id:'oldsighting01',at:new Date().toISOString(),note:'Original photo',photo:null,lat:51.52,lng:-0.1}]};
   window.__cats.set(legacy.id,legacy);boot();
  }''',old)
  await page.wait_for_function('window.whiskerBootComplete===true')
  assert await page.evaluate('speciesOf(s.cats[0])')=='Cat'
  await page.locator('[data-nav="dex"]').click()
  assert await page.locator('.bingo-tile.found').count()==1
  # save first snail through camera/gallery resulting form (no fictional computer vision)
  snail=picture((126,111,66))
  await page.evaluate('img=>{s.image=img;s.encounterAr=false;s.encounterLive=false;s.captureSummary=null;showCatForm(img)}',snail)
  await page.locator('#wildlife-species').select_option('Snail')
  assert await page.locator('#cat-coat').is_hidden()
  await page.locator('#cat-name').fill('Shelly')
  await page.locator('#wildlife-detail').fill('Garden snail')
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.wait_for_function('s.cats.length===2')
  records=await page.evaluate('s.cats.map(c=>({name:c.name,species:speciesOf(c),detail:c.speciesDetail,photo:c.photo,sightings:c.sightings.length}))')
  assert records[0]['name']=='Mochi' and records[0]['species']=='Cat'
  assert records[1]['name']=='Shelly' and records[1]['species']=='Snail' and records[1]['detail']=='Garden snail'
  assert records[1]['photo']==snail
  assert await page.locator('.bingo-tile.found').count()==1,'Snail must not affect Cat Bingo'
  assert 'Garden snail' in await page.locator('#view').inner_text()
  # species filtering
  await page.locator('[data-filter="Species:Snail"]').click()
  assert await page.locator('.cat-tile').count()==1
  assert 'Shelly' in await page.locator('.cat-tile').inner_text()
  # another species, the existing album should not be reset
  dog=picture((100,148,169))
  await page.evaluate('img=>{s.spottedSpecies="Cat";s.image=img;showCatForm(img)}',dog)
  await page.locator('#wildlife-species').select_option('Dog')
  await page.locator('#cat-name').fill('Buddy')
  await page.locator('#wildlife-detail').fill('Labrador mix')
  await page.locator('#real-cat').check()
  await page.locator('#pin-check').check()
  await page.evaluate('s.pendingApproxLocation={lat:51.54,lng:-0.13};s.pendingApproxLocationAt=Date.now()')
  await page.locator('#save-catch').click()
  await page.wait_for_function('s.cats.length===3')
  assert await page.evaluate('s.cats.find(c=>c.name==="Buddy").sightings[0].lat')==51.54
  assert await page.evaluate('s.cats.find(c=>c.name==="Buddy").species')=='Dog'
  await page.evaluate('s.filter="All";render()')
  await page.screenshot(path=str(ROOT/'WhiskerHunt_v3.8.0_FieldDex_Preview.png'),full_page=True)
  # revisit by species, do not show other species in previous-sighting picker
  again=picture((183,166,137))
  await page.evaluate('img=>{s.spottedSpecies="Dog";s.image=img;showCatForm(img)}',again)
  await page.locator('#wildlife-species').select_option('Dog')
  await page.locator('#mode-repeat').click()
  opts=await page.locator('#repeat-cat option').all_text_contents()
  assert len(opts)==1 and 'Buddy' in opts[0],opts
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.wait_for_function('s.cats.find(c=>c.name==="Buddy").sightings.length===2')
  # export backup + restore into empty simulated profile (v1 schema)
  payload=await page.evaluate('backupPayload()')
  assert payload['version']==1 and payload['app']=='Whisker Hunt'
  assert {c['species'] for c in payload['cats'] if 'species' in c}=={'Snail','Dog'}
  await page.evaluate('''async payload=>{s.cats=[];window.confirm=()=>true;await loadBackupText(JSON.stringify(payload))}''',payload)
  assert await page.evaluate('s.cats.length')==3
  assert await page.evaluate('s.cats.find(c=>c.name==="Buddy").sightings.length')==2
  assert await page.evaluate('speciesOf(s.cats.find(c=>c.name==="Mochi"))')=='Cat'
  assert await page.evaluate('s.cats.find(c=>c.name==="Shelly").speciesDetail')=='Garden snail'
  before_edit=await page.evaluate('''()=>{const c=s.cats.find(c=>c.name==='Buddy');return {photo:c.photo,visits:c.sightings.length,pin:c.sightings[0].lat}}''')
  await page.evaluate('''()=>openDetail(s.cats.find(c=>c.name==='Buddy').id)''')
  await page.locator('#edit-cat').click()
  assert await page.locator('#edit-species').input_value()=='Dog'
  await page.locator('#edit-species-detail').fill('Labrador retriever')
  await page.locator('#edit-save').click()
  after_edit=await page.evaluate('''()=>{const c=s.cats.find(c=>c.name==='Buddy');return {photo:c.photo,visits:c.sightings.length,pin:c.sightings[0].lat,detail:c.speciesDetail}}''')
  assert {k:after_edit[k] for k in ('photo','visits','pin')}==before_edit
  assert after_edit['detail']=='Labrador retriever'
  gpsfree=await page.evaluate('backupPayload(true)')
  assert all(all(v.get('lat') is None and v.get('lng') is None for v in c['sightings']) for c in gpsfree['cats'])
  assert not errors,errors
  print('PASS: old CatDex retained; snail/dog records, filters, repeat saves, v1 backup merge and GPS-free export')
  await browser.close()
if __name__=='__main__':asyncio.run(run())
