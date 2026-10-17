"""v2.9: automatic virtual cat spawn, no tap-to-place, collection separation."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'WhiskerHunt/Resources/Raw'

def make_photo():
    im=Image.new('RGB',(240,360),(90,125,160));buf=io.BytesIO();im.save(buf,format='JPEG')
    return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()

async def main():
    assert 'index_v29.html' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    assert '<ApplicationDisplayVersion>2.9.0</ApplicationDisplayVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationVersion>29</ApplicationVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert (RAW/'app_v29.js').read_bytes()==(ROOT/'BrowserPreview/app.js').read_bytes()
    assert (RAW/'style_v29.css').read_bytes()==(ROOT/'BrowserPreview/style.css').read_bytes()
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(RAW/'style_v29.css').read_text())
        await page.add_script_tag(content=(RAW/'app_v29.js').read_text())
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
        # Simulate a real-cat record; AR should not overwrite it or award real XP.
        orig=make_photo()
        await page.evaluate('''im => {const c={id:'real_1',name:'Mittens',coat:'Tabby',personality:'Curious',note:'',photo:im,createdAt:new Date().toISOString(),fav:false,sightings:[{id:'first_1',at:new Date().toISOString()}]};s.cats.push(c);s.profile.xp=99}''',orig)
        await page.evaluate('(im)=>showEncounter(im,{score:65,label:"Good",note:"Ready"},{live:true,ar:true})',orig)
        await page.locator('#encounter-stage').wait_for()
        assert await page.get_by_text('A cat appears automatically!',exact=False).count()==1
        assert await page.locator('details.ar-optional-models').count()==1
        assert await page.locator('details.ar-optional-models').get_attribute('open') is None
        assert await page.locator('#encounter-skip').count()==0
        assert await page.locator('#encounter-retake').count()==0
        assert 'not real-world surface tracking' in (await page.locator('#ar-smart-note').inner_text())
        # AR stage cannot be tap to place
        before=await page.evaluate('JSON.stringify(s.encounterFocus)')
        await page.locator('#encounter-stage').click(position={'x':35,'y':240},force=True)
        after=await page.evaluate('JSON.stringify(s.encounterFocus)')
        assert before==after,(before,after)
        # Make virtual model deterministic and catch it
        await page.locator('details.ar-optional-models summary').click()
        await page.locator('[data-ar-model="midnight-panther"]').click()
        await page.evaluate('handleEncounterHit("ball",.20)')
        await page.locator('#encounter-continue').wait_for(state='visible')
        assert await page.locator('#encounter-continue').inner_text()=='Keep this cat 🐾'
        await page.locator('#encounter-continue').click()
        await page.wait_for_function('s.cats.length===2')
        saved=await page.evaluate('''() => ({cats:s.cats.map(c=>({name:c.name,virtual:c.virtual||false,photo:(c.photo||'').slice(0,26),arModelHint:c.arModelHint,sightings:c.sightings.length})),xp:s.profile.xp})''')
        assert saved['xp']==99,saved
        assert saved['cats'][0]['name']=='Mittens' and not saved['cats'][0]['virtual']
        assert saved['cats'][1]['virtual'] and saved['cats'][1]['arModelHint']=='midnight-panther'
        assert saved['cats'][1]['photo'].startswith('data:image/png')
        assert await page.locator('.virtual-gallery').count()==1
        assert 'Mittens' in await page.locator('#dex-grid').inner_text()
        assert 'Black Cat' in await page.locator('.virtual-gallery').inner_text()
        assert 'Black Cat' not in await page.locator('#dex-grid').inner_text()
        assert await page.evaluate('weeklyQuests()[0].progress') in (0,1) # real only
        assert not errors,errors
        print('PASS v2.9: automatic placement, no tap, virtual image save, real cats/XP preserved, separated CatDex')
        await browser.close()
if __name__=='__main__': asyncio.run(main())
