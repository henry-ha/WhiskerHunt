"""Protect previously saved cats and fail visibly when optional location cannot be obtained."""
import asyncio, base64, io, re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
    im=Image.new('RGB',(220,260),(180,130,95)); out=io.BytesIO(); im.save(out,format='JPEG')
    return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
    js=(ROOT/'BrowserPreview/app.js').read_text()
    cs=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
    assert 'CountCats(string json)' in cs
    assert 'unexpected loss of saved cats' in cs
    assert 'allowEmpty: GetQuery(request, "allow-empty") == "1"' in cs
    assert 'window.whiskerNativeLocationError?.();' in cs
    assert 's.cats.length===0' in js
    assert 'PIN_NOT_SAVED' in js
    assert 'Source="index_v33.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    assert (ROOT/'WhiskerHunt/Resources/Raw/app_v33.js').read_text()==js
    assert '3.1.2' in js
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text()
        html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
        html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=js)
        await page.evaluate('''() => {
           window.__cats=new Map();window.__meta=new Map();
           window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{
             const tx={objectStore:(store)=>({put:(value)=>{
               const m=store==='cats'?window.__cats:window.__meta;
               m.set(store==='cats'?value.id:value.key,value);
             }})};setTimeout(()=>tx.oncomplete?.(),0);return tx;
           }});
           window.transact=async (store,mode,method,value)=>{
             const m=store==='cats'?window.__cats:window.__meta;
             if(method==='getAll')return Array.from(m.values());
             if(method==='get')return m.get(value);
             if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}
             if(method==='delete'){m.delete(value);return}
           };boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.evaluate('(im)=>{window.locationPrompt=async()=>null;showCatForm(im)}',photo())
        await page.locator('#cat-name').fill('Biscuit')
        await page.locator('#pin-check').check()
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.locator('#pin-failure:not(.hidden)').wait_for()
        assert await page.evaluate('s.cats.length')==0
        assert await page.locator('#pin-failure').is_visible()
        await page.locator('#pin-check').uncheck()
        await page.locator('#save-catch').click()
        await page.wait_for_function('s.cats.length===1')
        assert await page.evaluate('s.cats[0].sightings[0].lat') is None
        # Explicitly add an opt-in pin to an existing sighting while still at the location.
        await page.evaluate('window.locationPrompt=async()=>({lat:51.5234,lng:0.0876})')
        await page.evaluate('openDetail(s.cats[0].id)')
        await page.locator('[data-edit-sighting]').first.click()
        await page.locator('#add-current-pin').check()
        await page.locator('#save-sighting').click()
        await page.wait_for_function('s.cats[0].sightings[0].lat === 51.5234')
        assert await page.evaluate('s.cats[0].sightings[0].lng')==0.0876
        # Previous cat remains untouched if later virtual capture pin request fails.
        await page.evaluate('window.locationPrompt=async()=>null')
        await page.evaluate('''(im)=>{const model=AR_CAT_MODELS[0],habitat=AR_HABITATS[0];s.arModelKey=model.key;s.arHabitatKey=habitat.key;s.encounterAr=true;s.encounterCaptured=true;s.image=im;s.encounterFocus={x:.5,y:.5};showVirtualNamingForm()}''',photo())
        await page.locator('#virtual-pin').check()
        await page.locator('#virtual-save-final').click()
        await page.locator('#virtual-pin-failure:not(.hidden)').wait_for()
        assert await page.evaluate('s.cats.length')==1
        assert await page.evaluate('s.cats[0].name')=='Biscuit'
        assert not errors, errors
        print('PASS v3.1.2: optional pin failure is visible and blocks save; existing cats preserved; native guard present')
        await browser.close()
if __name__=='__main__': asyncio.run(main())
