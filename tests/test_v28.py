"""v2.8: AR safari prototype renders virtual cat models and preserves save compatibility."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'WhiskerHunt'/'Resources'/'Raw'

def image(rgb):
    im=Image.new('RGB',(240,300),rgb)
    out=io.BytesIO(); im.save(out,format='JPEG',quality=80)
    return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
    assert 'Source="index_v28.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    project=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationDisplayVersion>2.8.0</ApplicationDisplayVersion>' in project
    assert '<ApplicationVersion>28</ApplicationVersion>' in project
    entry=(RAW/'index_v28.html').read_text()
    assert 'app_v28.js' in entry and 'style_v28.css' in entry and 'whiskerAndroidShell=true' in entry
    assert (RAW/'app_v28.js').read_bytes()==(ROOT/'BrowserPreview/app.js').read_bytes()
    assert (RAW/'style_v28.css').read_bytes()==(ROOT/'BrowserPreview/style.css').read_bytes()
    sample=image((185,140,95))
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(RAW/'style_v28.css').read_text())
        await page.add_script_tag(content=(RAW/'app_v28.js').read_text())
        await page.evaluate("""() => {
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
        }""")
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.evaluate('(im)=>showEncounter(im,{score:73,label:"Good",note:"Ready"},{live:true,ar:true})',sample)
        await page.locator('#encounter-stage').wait_for()
        assert await page.get_by_text('AR safari').count()>=1
        assert await page.locator('.sheet.ar-sheet').count()==1
        assert await page.locator('[data-ar-model]').count()==6
        assert await page.locator('#encounter-ar-label').inner_text() != ''
        await page.locator('[data-ar-model="midnight-panther"]').click()
        assert await page.evaluate('s.arModelKey')=='midnight-panther'
        assert 'Black Cat' in await page.locator('#encounter-ar-label').inner_text()
        await page.locator('#encounter-skip').click()
        assert await page.locator('#cat-name').count()==1
        assert await page.locator('.info-note').last.inner_text() != ''
        # Save as a new cat and verify compatibility fields exist but schema still saves.
        await page.locator('#cat-name').fill('Shadow')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.wait_for_function('s.cats.length===1')
        saved=await page.evaluate('({name:s.cats[0].name,arHint:s.cats[0].arModelHint,captureMode:s.cats[0].sightings[0].captureMode,arModel:s.cats[0].sightings[0].arModel,xp:s.profile.xp})')
        assert saved['name']=='Shadow'
        assert saved['arHint']=='midnight-panther'
        assert saved['captureMode']=='ar-live'
        assert saved['arModel']=='midnight-panther'
        assert saved['xp']>=100
        assert not errors, errors
        print('PASS v2.8: AR safari UI, model switching, and save metadata work without breaking CatDex saves')
        await browser.close()
if __name__=='__main__': asyncio.run(main())
