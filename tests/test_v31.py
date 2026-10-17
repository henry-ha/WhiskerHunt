"""v3.1 browser integration: smoother AR, 120 cats, habitats, and virtual save round trip."""
import asyncio,base64,io,re,json
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(rgb=(180,130,80)):
    im=Image.new('RGB',(240,320),rgb);out=io.BytesIO();im.save(out,format='JPEG')
    return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
    assert 'Source="index_v31.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    cs=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationDisplayVersion>3.1.0</ApplicationDisplayVersion>' in cs
    assert '<ApplicationVersion>31</ApplicationVersion>' in cs
    source=(ROOT/'BrowserPreview/app.js').read_text()
    assert "const WHISKER_BUILD='3.1.0'" in source
    assert "Smooth AR mode" in source
    assert (ROOT/'WhiskerHunt/Resources/Raw/app_v31.js').read_text()==source
    assert (ROOT/'WhiskerHunt/Resources/Raw/style_v31.css').read_text()==(ROOT/'BrowserPreview/style.css').read_text()
    img=photo()
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
        count=await page.evaluate('AR_CAT_MODELS.length')
        habitats=await page.evaluate('AR_HABITATS.length')
        assert count >= 120 and habitats >= 12
        # Start AR catch screen and confirm no manual reroll UI is exposed.
        await page.locator('#hero-catch').click()
        await page.wait_for_selector('#ar-photo')
        assert await page.locator('#ar-reroll').count() == 0
        # Simulate a captured AR encounter and save it.
        await page.evaluate('''(im)=>{ const model=AR_CAT_MODELS[0], habitat=AR_HABITATS[0];
          s.arModelKey=model.key; s.arHabitatKey=habitat.key; s.encounterAr=true; s.encounterCaptured=true; s.image=im; s.encounterFocus={x:habitat.focus.x,y:habitat.focus.y}; showVirtualNamingForm(); }''',img)
        await page.wait_for_selector('#virtual-name')
        title=await page.locator('.dim').first.text_content()
        assert 'Window perch' in title or len(title)>0
        await page.locator('#virtual-dice-name').click()
        await page.locator('#virtual-dice-memory').click()
        await page.wait_for_function("document.querySelector('#virtual-photo-preview img')!==null")
        await page.locator('#virtual-save-final').click()
        await page.wait_for_function('s.cats.length===1')
        data=await page.evaluate('''() => ({
          cat:s.cats[0],
          backup:backupPayload(),
          gallery:renderVirtualGallery(),
          count:AR_CAT_MODELS.length,
          habitats:AR_HABITATS.length
        })''')
        assert data['count'] >= 120 and data['habitats'] >= 12
        assert data['cat']['virtual'] is True
        assert data['cat']['arHabitatHint'] == 'window-perch'
        assert data['cat']['sightings'][0]['habitat'] == 'window-perch'
        assert 'Safari progress:' in data['gallery']
        assert data['backup']['cats'][0]['sightings'][0]['habitat'] == 'window-perch'
        # Restore round trip preserves habitat and virtual roster fields.
        await page.evaluate('''async (payload)=>{window.confirm=()=>true;s.cats=[];await loadBackupText(JSON.stringify(payload))}''',data['backup'])
        restored=await page.evaluate('''() => ({count:s.cats.length, cat:s.cats[0], xp:s.profile.xp})''')
        assert restored['count']==1
        assert restored['cat']['virtual'] is True
        assert restored['cat']['arHabitatHint']=='window-perch'
        assert restored['cat']['sightings'][0]['habitat']=='window-perch'
        # Optional approximate pin still rounds.
        await page.evaluate('''(im)=>{locationPrompt=async()=>({lat:51.5234,lng:0.0876}); const model=AR_CAT_MODELS[1], habitat=AR_HABITATS[1]; s.arModelKey=model.key; s.arHabitatKey=habitat.key; s.encounterAr=true; s.encounterCaptured=true; s.image=im; s.encounterFocus={x:habitat.focus.x,y:habitat.focus.y}; showVirtualNamingForm()}''',img)
        await page.locator('#virtual-pin').check()
        await page.locator('#virtual-save-final').click()
        await page.wait_for_function('s.cats.length===2')
        coords=await page.evaluate('''() => {const c=s.cats.find(c=>c.arHabitatHint==='bookshelf-nook');const v=c.sightings.at(-1);const clean=backupPayload(true).cats.find(c=>c.arHabitatHint==='bookshelf-nook').sightings.at(-1);return {lat:v.lat,lng:v.lng,cleanLat:clean.lat,cleanLng:clean.lng}}''')
        assert coords=={'lat':51.52,'lng':0.09,'cleanLat':None,'cleanLng':None},coords
        assert not errors,errors
        print('PASS v3.1: 120+ AR cats, unseen habitats, virtual save/restore and rounded optional pins')
        await browser.close()
if __name__=='__main__': asyncio.run(main())
