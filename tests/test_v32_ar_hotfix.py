"""v3.1.1: regression for Android's 'arMode is not defined' AR Safari failure."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
    im=Image.new('RGB',(300,400),(160,123,92))
    b=io.BytesIO();im.save(b,format='JPEG')
    return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()

async def main():
    entry=(ROOT/'WhiskerHunt/Resources/Raw/index_v32.html').read_text()
    xaml=(ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    project=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert 'Source="index_v32.html"' in xaml
    assert 'src="app_v32.js"' in entry and 'href="style_v32.css"' in entry
    assert '3.1.1-32' in entry and 'ApplicationVersion>32<' in project
    assert (ROOT/'WhiskerHunt.sln').exists()
    assert (ROOT/'BrowserPreview/app_v32.js').read_bytes()==(ROOT/'WhiskerHunt/Resources/Raw/app_v32.js').read_bytes()
    assert (ROOT/'BrowserPreview/style_v32.css').read_bytes()==(ROOT/'WhiskerHunt/Resources/Raw/style_v32.css').read_bytes()
    source=(ROOT/'BrowserPreview/app_v32.js').read_text()
    # No incorrectly scoped arMode in unrelated functions.
    assert 'const model=getArModel(s.arModelKey);\n const mount=' in source
    assert 'if(arMode&&habitat)' not in source[source.index('function refreshArEncounterUi()'):source.index('const originalOpenModal=')]
    assert 'if(arMode&&habitat)' not in source[source.index('showCatForm=function(image)'):source.index('saveCatch=function')]
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'],headless=True)
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index_v32.html').read_text().replace('<script src="app_v32.js" defer></script>','').replace('<link rel="stylesheet" href="style_v32.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style_v32.css').read_text())
        await page.add_script_tag(content=source)
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
          };
          boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        # Exact v3.1 failure: beginEncounter -> showEncounter -> refreshArEncounterUi.
        await page.evaluate('(image)=>beginEncounter(image,{live:true,ar:true})',photo())
        await page.locator('#encounter-ar-cat').wait_for()
        assert await page.get_by_text('AR safari ✨').count()==1
        assert 'build 32' in await page.locator('.whisker-build-stamp').inner_text()
        assert await page.locator('#encounter-ar-label').inner_text() != ''
        assert await page.locator('#ar-reroll').count()==0
        assert await page.evaluate('AR_CAT_MODELS.length')==120
        assert await page.evaluate('AR_HABITATS.length')==12
        assert not errors,errors
        # Complete real capture flow, then save AR image and compatible metadata.
        await page.evaluate('handleEncounterHit("ball",0.2)')
        await page.locator('#encounter-continue').wait_for(state='visible',timeout=5000)
        await page.locator('#encounter-continue').click()
        await page.locator('#virtual-name').wait_for(timeout=5000)
        await page.wait_for_function('document.querySelector("#virtual-photo-preview img")?.complete === true',timeout=10000)
        await page.locator('#virtual-save-final').click()
        await page.wait_for_function('s.cats.length===1')
        cat=await page.evaluate('({id:s.cats[0].id,virtual:s.cats[0].virtual,habitat:s.cats[0].arHabitatHint,photo:s.cats[0].photo,sightings:s.cats[0].sightings.length})')
        assert cat['virtual'] and cat['habitat'] and cat['sightings']==1
        assert cat['photo'].startswith('data:image/')
        assert not errors, errors
        print('PASS: v3.1.1 AR Safari opens, 120 cats render, capture/save succeeds, Android versioned assets verified')
        await browser.close()

if __name__=='__main__':asyncio.run(main())
