"""v1.3: real pointer dragging, target repositioning, lure enlargement and save compatibility."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(rgb=(95,143,164)):
    im=Image.new('RGB',(600,400),rgb)
    buf=io.BytesIO(); im.save(buf,format='JPEG',quality=85)
    return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844},has_touch=True)
        errors=[];page.on('pageerror',lambda ex:errors.append(str(ex)))
        html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
        await page.evaluate('''() => {window.__cats=new Map();window.__meta=new Map();
          window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value);}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
          window.transact=async (store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;
            if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);
            if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}
            if(method==='delete'){m.delete(value);return}};boot();}''')
        await page.wait_for_function('window.whiskerBootComplete')
        await page.evaluate('(im)=>beginEncounter(im)',photo())
        await page.locator('#encounter-stage').wait_for()
        await page.wait_for_function('document.getElementById("encounter-cat-crop").src.startsWith("data:image/jpeg")')
        assert await page.get_by_text('Photo clarity estimate:').count()==1
        # Tap in image and confirm the real target follows the selected focus.
        target=await page.locator('#encounter-photo').bounding_box()
        await page.mouse.click(target['x']+target['width']*.70,target['y']+target['height']*.35)
        await page.wait_for_timeout(350)
        newx=await page.evaluate('s.encounterFocus.x')
        assert .62<newx<.78, newx
        # Drag lure to the target, rather than calling the result handler directly.
        async def actual_drag():
            launcher=await page.locator('#throw-item').bounding_box()
            cat=await page.locator('#encounter-cat').bounding_box()
            sx=launcher['x']+launcher['width']/2;sy=launcher['y']+launcher['height']/2
            tx=cat['x']+cat['width']/2;ty=cat['y']+cat['height']/2
            await page.mouse.move(sx,sy)
            await page.mouse.down()
            await page.mouse.move(tx,ty,steps=16)
            await page.mouse.up()
        await page.locator('#tool-lure').click()
        await actual_drag()
        assert await page.evaluate('s.encounterLured'), 'Lure did not register an actual drag gesture'
        assert 'curious' in (await page.locator('#encounter-cat').get_attribute('class'))
        assert await page.evaluate('s.encounterTool')=='ball'
        # Intentional miss should NOT capture.
        launcher=await page.locator('#throw-item').bounding_box()
        sx=launcher['x']+launcher['width']/2;sy=launcher['y']+launcher['height']/2
        await page.mouse.move(sx,sy);await page.mouse.down();await page.mouse.move(sx+45,sy-18,steps=8);await page.mouse.up()
        assert not await page.evaluate('s.encounterCaptured')
        assert await page.get_by_text('Missed with Whisker Pod',exact=False).count()>0
        await actual_drag()
        assert await page.evaluate('s.encounterCaptured')
        await page.locator('#encounter-continue').wait_for()
        assert await page.evaluate('s.captureSummary.throwRating') in ('Nice!','Great!','Purrfect!')
        await page.screenshot(path=str(ROOT/'tests/v13-encounter-captured.png'))
        await page.locator('#encounter-continue').click()
        await page.locator('#cat-name').fill('Whiskers')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.get_by_text('Whiskers',exact=True).first.wait_for()
        assert await page.evaluate('s.cats.length')==1
        assert await page.evaluate('s.profile.xp')>=100
        # Closing during image assessment must not reopen the dialog.
        await page.evaluate('''() => {startCatch();beginEncounter(s.cats[0].photo);closeModal()}''')
        await page.wait_for_timeout(500)
        assert await page.locator('#modal-layer').evaluate('el=>el.classList.contains("hidden")')
        assert (ROOT/'BrowserPreview/app.js').read_text()==(ROOT/'WhiskerHunt/Resources/Raw/app.js').read_text()
        assert (ROOT/'BrowserPreview/style.css').read_text()==(ROOT/'WhiskerHunt/Resources/Raw/style.css').read_text()
        assert 'builder.Logging.AddDebug();' not in (ROOT/'WhiskerHunt/MauiProgram.cs').read_text()
        assert 'Microsoft.Maui.Controls' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
        assert not errors,errors
        print('PASS v1.3: touch-friendly pointer drag, focus crop, lure, miss/retry, two-shake capture, save, dismissal guard, MAUI build fix')
        await browser.close()

if __name__=='__main__': asyncio.run(main())
