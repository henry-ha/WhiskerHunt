"""v3.3: visual switches, recovery preview, additive backup merge, version consistency."""
import asyncio,base64,io,re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(rgb):
 im=Image.new('RGB',(240,300),rgb);f=io.BytesIO();im.save(f,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(f.getvalue()).decode()

async def main():
 cs=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert '<ApplicationDisplayVersion>3.3.0</ApplicationDisplayVersion>' in cs
 assert '<ApplicationVersion>35</ApplicationVersion>' in cs
 assert 'Source="index_v35.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
 for d in [ROOT/'BrowserPreview',ROOT/'WhiskerHunt/Resources/Raw']:
  assert 'app_v35.js' in (d/'index_v35.html').read_text()
  assert 'style_v35.css' in (d/'index_v35.html').read_text()
  assert '3.3.0-35' in (d/'index_v35.html').read_text()
  assert (d/'app_v35.js').read_text()==(d/'app.js').read_text()
  assert (d/'style_v35.css').read_text()==(d/'style.css').read_text()
 native=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
 assert 'PreviewRecoveryCopyAsync' in native and 'OfferRecoveryMergeAsync' in native
 assert 'ExportCurrentWithoutSavingAsync' in native
 assert 'that would rotate .bak' in native
 source=(ROOT/'BrowserPreview/app.js').read_text()
 assert 'whiskerRecoveryPreview' in source and 'whiskerRecoveryImport' in source
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
  html=(ROOT/'BrowserPreview/index.html').read_text()
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
  await page.add_script_tag(content=source)
  await page.evaluate('''() => {
    window.__cats=new Map();window.__meta=new Map();
    window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{
      const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value)}})};
      setTimeout(()=>tx.oncomplete?.(),0);return tx;
    }});
    window.transact=async(store,mode,method,value)=>{
     const m=store==='cats'?window.__cats:window.__meta;
     if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);
     if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}
     if(method==='delete'){m.delete(value);return}
    };boot();
  }''')
  await page.wait_for_function('window.whiskerBootComplete===true')
  a=photo((180,160,130))
  await page.evaluate('(img)=>showEncounter(img,{score:80,label:"Good",note:"ok"},{live:false})',a)
  assert await page.locator('#tool-ball').is_hidden()
  assert await page.locator('#tool-lure').is_visible()
  assert await page.locator('#tool-lure').get_attribute('aria-label')=='Switch to Lure'
  await page.locator('#tool-lure').click()
  assert await page.locator('#tool-lure').is_hidden()
  assert await page.locator('#tool-ball').is_visible()
  assert await page.locator('#tool-ball').get_attribute('aria-label')=='Switch to Paw'
  assert 'tool-switch-pop' in (await page.locator('#throw-item').get_attribute('class'))
  await page.evaluate('handleEncounterHit("lure")')
  assert await page.locator('#tool-ball').is_hidden()
  assert await page.locator('#tool-lure').is_visible()
  assert await page.locator('.paw-claw').count()>=4
  # The AR HUD hides the verbose hints, retaining the compact help line.
  await page.evaluate('(img)=>{s.arModelKey=AR_CAT_MODELS[0].key;s.arHabitatKey=AR_HABITATS[0].key;showEncounter(img,{score:0,label:"Live",note:"ok"},{ar:true,live:true})}',a)
  assert await page.locator('.sheet.ar-sheet').count()==1
  assert await page.locator('.encounter-quick-help').is_visible()
  assert await page.locator('.encounter-quality').is_hidden()
  await page.screenshot(path=str(ROOT/'WhiskerHunt_v3.3_AR_CleanHUD.png'),full_page=True)
  # Recovery wizard in browser, simulated native snapshot metadata (no photo payload).
  await page.evaluate('window.closeModal();navigate("profile")')
  await page.locator('[data-action="recovery-wizard"]').click()
  assert await page.locator('#recovery-result').is_visible()
  await page.evaluate('window.whiskerRecoveryPreview({available:true,cats:[{id:"oldercat",name:"Mochi",sightings:1}]})')
  assert 'Mochi' in await page.locator('#recovery-result').inner_text()
  assert await page.locator('#recovery-merge').is_enabled()
  # A real backup merge must be additive and only proceed with confirmation.
  backup=await page.evaluate('''(img)=>({app:'Whisker Hunt',version:1,cats:[{
    id:'oldercat',name:'Mochi',coat:'Tabby',personality:'Playful',note:'From old backup',photo:img,
    signature:'unique',createdAt:new Date().toISOString(),fav:false,
    sightings:[{id:'old-sighting',at:new Date().toISOString(),note:'hello',photo:null}]
  }],profile:{name:'Cat Explorer',xp:250,claimed:[]}})''',a)
  count=await page.evaluate('s.cats.length')
  await page.evaluate('window.confirm=()=>false')
  await page.evaluate('async (data)=>{await window.whiskerRecoveryImport(JSON.stringify(data))}',backup)
  assert await page.evaluate('s.cats.length')==count
  await page.evaluate('window.confirm=()=>true')
  await page.evaluate('async (data)=>{await window.whiskerRecoveryImport(JSON.stringify(data))}',backup)
  assert await page.evaluate('s.cats.length')==count+1
  assert await page.evaluate('s.cats[0].name')=='Mochi'
  assert await page.evaluate('s.profile.xp')>=250
  assert not errors,errors
  print('PASS v3.3: switcher/HUD, non-destructive recovery preview, confirmation and additive restore')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
