"""v2.7: best-shot review changes chosen CatDex image without altering data schema."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'WhiskerHunt/Resources/Raw'

def image(rgb):
    im=Image.new('RGB',(240,300),rgb)
    out=io.BytesIO(); im.save(out,format='JPEG',quality=80)
    return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
    assert 'Source="index_v27.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    assert '<ApplicationDisplayVersion>2.7.0</ApplicationDisplayVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationVersion>27</ApplicationVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    entry=(RAW/'index_v27.html').read_text()
    assert 'app_v27.js' in entry and 'style_v27.css' in entry and 'whiskerAndroidShell=true' in entry
    assert (RAW/'app_v27.js').read_bytes()==(ROOT/'BrowserPreview/app.js').read_bytes()
    assert (RAW/'style_v27.css').read_bytes()==(ROOT/'BrowserPreview/style.css').read_bytes()
    a,b,c=image((70,130,180)),image((180,90,80)),image((100,170,100))
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(RAW/'style_v27.css').read_text())
        await page.add_script_tag(content=(RAW/'app_v27.js').read_text())
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
        await page.evaluate('(im)=>showEncounter(im,{score:75,label:"Good",note:"Photo ready"},{live:true})',a)
        await page.locator('#encounter-stage').wait_for()
        assert await page.get_by_text('① Tap the cat').count()==1
        assert await page.locator('details.encounter-help').count()==1
        assert await page.locator('.whisker-build-stamp').inner_text()=='Whisker Hunt v2.7.0 · build 27'
        frames=[{'image':a,'quality':{'label':'Good','score':75},'subjectQuality':{'label':'Good','score':75}},
                {'image':b,'quality':{'label':'Great','score':80},'subjectQuality':{'label':'Great','score':81}},
                {'image':c,'quality':{'label':'Fair','score':52},'subjectQuality':{'label':'Fair','score':54}}]
        await page.evaluate('(frames)=>displayCaptureShotChoices(frames)',frames)
        assert await page.locator('.shot-option').count()==3
        assert await page.locator('.shot-option.selected').count()==1
        await page.locator('[data-shot="1"]').click()
        assert await page.evaluate('s.image')==b
        assert await page.locator('[data-shot="1"]').get_attribute('aria-pressed')=='true'
        assert await page.locator('#encounter-photo').get_attribute('src')==b
        await page.locator('#encounter-skip').click()
        assert await page.locator('#cat-name').count()==1
        assert await page.locator('.photo-preview').get_attribute('src')==b
        await page.locator('#cat-name').fill('Mochi')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.wait_for_function('s.cats.length===1')
        saved=await page.evaluate('({photo:s.cats[0].photo,sightings:s.cats[0].sightings.length,xp:s.profile.xp})')
        assert saved['photo']==b and saved['sightings']==1 and saved['xp']>=100,saved
        await page.locator('#nav-catch').click()
        assert await page.evaluate('captureShots.length')==0
        await page.locator('[data-close]').first.click()
        assert not errors,errors
        print('PASS v2.7: native asset paths, thumbnail choosing, save selected CatDex image, no transient leakage')
        await browser.close()
if __name__=='__main__': asyncio.run(main())
