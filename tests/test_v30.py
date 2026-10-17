"""v3.0 browser integration: names, memories, photo batches, virtual scene composite and private backups."""
import asyncio,base64,io,re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(rgb):
    im=Image.new('RGB',(240,320),rgb);out=io.BytesIO();im.save(out,format='JPEG')
    return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
    assert 'Source="index_v30.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    assert '<ApplicationDisplayVersion>3.0.0</ApplicationDisplayVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationVersion>30</ApplicationVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    source=(ROOT/'BrowserPreview/app.js').read_text()
    assert 'const WHISKER_BUILD=\'3.0.0\'' in source
    assert (ROOT/'WhiskerHunt/Resources/Raw/app_v30.js').read_text()==source
    assert (ROOT/'WhiskerHunt/Resources/Raw/style_v30.css').read_text()==(ROOT/'BrowserPreview/style.css').read_text()
    img_a,img_b=photo((40,82,150)),photo((180,130,80))
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text()
        html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
        html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=source)
        await page.evaluate('''() => {
           window.__cats=new Map();window.__meta=new Map();
           window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{
             const tx={objectStore:(store)=>({put:(value)=>{
               const m=store==='cats'?window.__cats:window.__meta;
               m.set(store==='cats'?value.id:value.key,value);
             }})};setTimeout(()=>tx.oncomplete?.(),0);return tx;
           }});
           window.transact=async(store,mode,method,value)=>{
             const m=store==='cats'?window.__cats:window.__meta;
             if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);
             if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}
             if(method==='delete'){m.delete(value);return}
           };boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        # Photo batch adds two, previews and deletes one, Done chooses selected photo
        await page.locator('#hero-catch').click()
        await page.wait_for_selector('#take-photo')
        assert await page.evaluate('AR_CAT_MODELS.length') == 30
        await page.evaluate('(im)=>{multiPhotoActive=true;deliverPhoto(im)}',img_a)
        assert await page.locator('.batch-thumb').count()==1
        await page.evaluate('(im)=>deliverPhoto(im)',img_b)
        assert await page.locator('.batch-thumb').count()==2
        await page.locator('[data-batch="0"]').click()
        await page.locator('#batch-delete').click()
        assert await page.locator('.batch-thumb').count()==1
        await page.locator('#batch-done').click()
        await page.wait_for_selector('#encounter-stage')
        assert await page.evaluate('s.image')==img_b
        await page.locator('#encounter-skip').click()
        await page.wait_for_selector('#cat-name')
        assert await page.locator('#dice-name').count()==1 and await page.locator('#dice-memory').count()==1
        await page.locator('#dice-name').click();await page.locator('#dice-memory').click()
        assert (await page.locator('#cat-name').input_value()).strip()
        assert (await page.locator('#cat-note').input_value()).strip()
        assert await page.locator('#pin-check').is_checked() is False
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.wait_for_function('s.cats.length===1')
        # Virtual scene photo includes camera background + cat sprite; user names it.
        await page.evaluate('''(im)=>{s.arModelKey="ginger-tabby";s.encounterAr=true;s.encounterCaptured=true;s.image=im;s.encounterFocus={x:.5,y:.6};showVirtualNamingForm()}''',img_b)
        await page.wait_for_selector('#virtual-name')
        await page.locator('#virtual-dice-name').click()
        virtual_name=await page.locator('#virtual-name').input_value()
        assert virtual_name
        await page.locator('#virtual-dice-memory').click()
        await page.wait_for_function("document.querySelector('#virtual-photo-preview img')!==null")
        await page.locator('#virtual-save-final').click()
        await page.wait_for_function('s.cats.length===2')
        saved=await page.evaluate('''() => ({
          virtual:s.cats.find(c=>c.virtual),
          real:s.cats.find(c=>!c.virtual),
          backup:backupPayload(),
          arCount:AR_CAT_MODELS.length
        })''')
        assert saved['virtual']['name']==virtual_name
        assert saved['virtual']['note']
        assert saved['virtual']['photo'].startswith('data:image/jpeg;base64,')
        assert saved['virtual']['sightings'][0]['lat'] is None
        assert saved['backup']['version']==1 and len(saved['backup']['cats'])==2
        assert saved['real']['photo']==img_b
        assert saved['arCount']==30
        # Restore must preserve virtual status, AR model, and both photo records.
        await page.evaluate('''async (payload)=>{window.confirm=()=>true;s.cats=[];await loadBackupText(JSON.stringify(payload))}''',saved['backup'])
        recovered=await page.evaluate('''() => ({count:s.cats.length, virtual:s.cats.find(c=>c.virtual), real:s.cats.find(c=>!c.virtual),xp:s.profile.xp})''')
        assert recovered['count']==2 and recovered['virtual']['arModelHint']=='ginger-tabby'
        assert recovered['real']['photo']==img_b
        assert recovered['virtual']['photo'].startswith('data:image/jpeg;base64,')
        # Optional approximate pin is rounded and stays out of GPS-free backup.
        await page.evaluate('''(im)=>{locationPrompt=async()=>({lat:51.5234,lng:0.0876});s.arModelKey='ginger-tabby';s.encounterAr=true;s.encounterCaptured=true;s.image=im;s.encounterFocus={x:.5,y:.6};showVirtualNamingForm()}''',img_b)
        await page.locator('#virtual-pin').check()
        await page.locator('#virtual-save-final').click()
        await page.wait_for_function('s.cats.find(c=>c.virtual).sightings.length===2')
        coords=await page.evaluate('''() => {const c=s.cats.find(c=>c.virtual);const v=c.sightings.at(-1);const clean=backupPayload(true).cats.find(c=>c.virtual).sightings.at(-1);return {lat:v.lat,lng:v.lng,cleanLat:clean.lat,cleanLng:clean.lng}}''')
        assert coords=={'lat':51.52,'lng':0.09,'cleanLat':None,'cleanLng':None},coords
        await page.locator('#head-profile').click()
        assert await page.get_by_text('Save full backup',exact=False).count()>=1
        assert await page.get_by_text('GPS-free backup',exact=False).count()>=1
        assert not errors,errors
        print('PASS v3.0: 30 models, multi-photo add/delete/Done, dice fields, virtual scene photo, CatDex and backup integrity')
        await browser.close()
if __name__=='__main__': asyncio.run(main())
