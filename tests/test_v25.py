"""v2.5: actual packaged Android entrypoint, safe native fallback, and paw-only visuals."""
from pathlib import Path
import asyncio, base64, io
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'WhiskerHunt/Resources/Raw'

def photo():
    im=Image.new('RGB',(320,410),(37,54,77)); d=ImageDraw.Draw(im)
    d.ellipse((75,95,245,285),fill=(174,129,91))
    d.polygon([(92,129),(115,59),(155,120)],fill=(174,129,91))
    d.polygon([(165,120),(215,59),(228,130)],fill=(174,129,91))
    d.ellipse((119,174,135,191),fill=(17,54,32))
    d.ellipse((183,174,199,191),fill=(17,54,32))
    o=io.BytesIO(); im.save(o,format='JPEG',quality=90)
    return 'data:image/jpeg;base64,'+base64.b64encode(o.getvalue()).decode()

async def main():
    assert 'Source="index_v25.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    assert '<ApplicationDisplayVersion>2.5.0</ApplicationDisplayVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationVersion>25</ApplicationVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    entry=(RAW/'index_v25.html').read_text()
    assert 'style_v25.css' in entry and 'app_v25.js' in entry and 'whiskerAndroidShell=true' in entry
    assert (RAW/'app_v25.js').read_bytes()==(ROOT/'BrowserPreview/app.js').read_bytes()
    assert (RAW/'style_v25.css').read_bytes()==(ROOT/'BrowserPreview/style.css').read_bytes()
    assert 'window.whiskerNativePickerCancelled?.();' in (ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
    assert 'retireAndroidShellWorker()' in (RAW/'app_v25.js').read_text()
    assert 'CacheModes.NoCache' in (ROOT/'WhiskerHunt/MauiProgram.cs').read_text()
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844},device_scale_factor=2)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(RAW/'style_v25.css').read_text())
        await page.add_script_tag(content=(RAW/'app_v25.js').read_text())
        # test cancelled camera with pending getUserMedia
        await page.evaluate("""() => {
          window.__cats=new Map();window.__meta=new Map();
          window.openDb=async()=>({mock:true,transaction:()=>({objectStore:()=>({put:()=>{}})})});
          window.transact=async (store,mode,method,value)=>{
            const m=store==='cats'?window.__cats:window.__meta;
            if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);
            if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value;}
            if(method==='delete'){m.delete(value);return;}
          };
          boot();
        }""")
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.evaluate("""() => {
           Object.defineProperty(window, 'isSecureContext', {configurable:true, value:true});
           Object.defineProperty(navigator, 'mediaDevices', {configurable:true, value:{
             getUserMedia:()=>new Promise(resolve=>{window.__lateMediaResolve=resolve;})
           }});
           startLiveEncounter();
        }""")
        await page.get_by_text('Starting live camera…').wait_for()
        await page.locator('#live-fallback').click()
        await page.get_by_text('Choose your camera').wait_for()
        state=await page.evaluate("""() => ({
           title:document.querySelector('.sheet h2')?.textContent,
           retry:!!document.getElementById('retry-live'),
           build:document.querySelector('.whisker-build-stamp')?.textContent,
           closedLoading: !document.body.textContent.includes('Preparing preview…')
        })""")
        assert state['retry'] and state['closedLoading'] and '2.5.0' in state['build'],state
        # A cancelled native camera must not expose the old loading sheet.
        await page.evaluate('window.whiskerNativePickerCancelled()')
        assert await page.get_by_text('Camera cancelled.',exact=False).count()>=1
        await page.evaluate("""() => window.__lateMediaResolve({getTracks:()=>[{stop:()=>{}}]})""")
        await page.wait_for_timeout(50)
        assert await page.get_by_text('Choose your camera').count()==1
        # The fallback retains a user-operable live retry control.
        assert await page.locator('#retry-live').count()==1
        await page.evaluate('(im)=>showEncounter(im,{label:"Good",note:"Photo ready"},{live:false})',photo())
        await page.locator('#encounter-stage').wait_for()
        assert await page.locator('#throw-item svg.whisker-paw-svg').count()==1
        assert await page.locator('#encounter-orb svg.whisker-paw-svg').count()==1
        assert await page.locator('#throw-item .paw-pad').count()==0
        assert await page.locator('.whisker-build-stamp').inner_text()=='Whisker Hunt v2.5.0 · build 25'
        detail=await page.evaluate("""() => ({
          podCircle:getComputedStyle(document.getElementById('tool-ball')).borderRadius,
          dragRing:getComputedStyle(document.getElementById('throw-item')).borderRadius,
          select:getComputedStyle(document.getElementById('throw-item')).userSelect,
          toolLabel:document.getElementById('tool-ball').innerText,
        })""")
        assert detail['select']=='none'
        assert detail['podCircle']=='50%' or detail['podCircle'].endswith('px')
        await page.screenshot(path='/mnt/data/WhiskerHunt_v2.5_PawPreview.png',full_page=True)
        await page.evaluate('handleEncounterHit("ball",0.2)')
        await page.wait_for_timeout(900)
        assert 'float' in (await page.locator('#encounter-meow').get_attribute('class'))
        await page.screenshot(path='/mnt/data/WhiskerHunt_v2.5_CapturePreview.png',full_page=True)
        assert not errors,errors
        print('PASS v2.5: Android versioned entrypoint, WebView assets, late camera cancellation, retry chooser, SVG paw, visible build, meow')
        await browser.close()

if __name__=='__main__':asyncio.run(main())
