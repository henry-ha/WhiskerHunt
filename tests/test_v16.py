"""v1.6: live pointer aim, minimum drag, cancellation and unchanged CatDex save."""
import asyncio,base64,io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
    im=Image.new('RGB',(600,400),'#7c9eaf');b=io.BytesIO();im.save(b,format='JPEG')
    return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844},has_touch=True)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
        await page.evaluate('''() => {window.__cats=new Map();window.__meta=new Map();
          window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value);}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
          window.transact=async (store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete'){m.delete(value);return}};boot();}''')
        await page.wait_for_function('window.whiskerBootComplete')
        await page.evaluate('(im)=>beginEncounter(im)',photo())
        await page.locator('#encounter-stage').wait_for()
        await page.wait_for_function('document.getElementById("encounter-cat-crop").src.startsWith("data:image/jpeg")')
        async def positions():
            a=await page.locator('#throw-item').bounding_box()
            b=await page.locator('#encounter-cat').bounding_box()
            return (a['x']+a['width']/2,a['y']+a['height']/2),(b['x']+b['width']/2,b['y']+b['height']/2)
        (sx,sy),(tx,ty)=await positions()
        # Tiny motion should not count as a throw.
        await page.mouse.move(sx,sy);await page.mouse.down();await page.mouse.move(sx+8,sy-5,steps=2)
        assert await page.locator('#encounter-aim-guide').is_visible()
        await page.mouse.up()
        assert not await page.evaluate('s.encounterCaptured')
        assert not await page.locator('#encounter-aim-guide').is_visible()
        assert await page.get_by_text('Hold and drag the selected tool',exact=False).count()==1
        # A deliberate miss should show the aim guide but never save anything.
        await page.mouse.move(sx,sy);await page.mouse.down();await page.mouse.move(sx+55,sy-65,steps=6)
        assert await page.locator('#encounter-aim-guide').is_visible()
        assert not await page.locator('#encounter-aim-guide').evaluate('el=>el.classList.contains("aim-hit")')
        await page.mouse.up()
        assert not await page.evaluate('s.encounterCaptured')
        assert await page.evaluate('s.cats.length')==0
        # Cancel a real captured pointer and ensure transient UI is removed.
        await page.mouse.move(sx,sy);await page.mouse.down();await page.mouse.move(sx+45,sy-45,steps=4)
        assert await page.locator('#encounter-aim-guide').is_visible()
        await page.evaluate('''() => {const item=document.getElementById('throw-item');item.dispatchEvent(new PointerEvent('pointercancel',{pointerId:1,bubbles:true}));}''')
        assert not await page.locator('#encounter-aim-guide').is_visible()
        await page.mouse.up()
        assert not await page.evaluate('s.encounterCaptured')
        # Use the real drag to land a lure and verify the green guide.
        await page.locator('#tool-lure').click()
        (sx,sy),(tx,ty)=await positions()
        await page.mouse.move(sx,sy);await page.mouse.down();await page.mouse.move(tx,ty,steps=12)
        assert await page.locator('#encounter-aim-guide').evaluate('el=>el.classList.contains("aim-hit")')
        assert await page.locator('#encounter-cat').evaluate('el=>el.classList.contains("aim-hit")')
        assert await page.get_by_text('On target!',exact=False).count()==1
        await page.screenshot(path=str(ROOT/'tests/v16-live-aim.png'),full_page=True)
        await page.mouse.up()
        assert await page.evaluate('s.encounterLured')
        assert await page.evaluate('s.encounterTool')=='ball'
        assert not await page.locator('#encounter-aim-guide').is_visible()
        # The same aim geometry should capture with the ball.
        (sx,sy),(tx,ty)=await positions()
        await page.mouse.move(sx,sy);await page.mouse.down();await page.mouse.move(tx,ty,steps=12)
        assert await page.locator('#encounter-aim-guide').evaluate('el=>el.classList.contains("aim-hit")')
        await page.mouse.up()
        assert await page.evaluate('s.encounterCaptured')
        assert await page.evaluate('s.cats.length')==0
        await page.locator('#encounter-continue').wait_for()
        await page.locator('#encounter-continue').click()
        await page.locator('#cat-name').fill('Guidecat')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.get_by_text('Guidecat',exact=True).first.wait_for()
        assert await page.evaluate('s.cats.length')==1
        assert await page.evaluate('s.cats[0].sightings.length')==1
        assert await page.evaluate('s.profile.xp')>=100
        assert (ROOT/'BrowserPreview/app.js').read_text()==(ROOT/'WhiskerHunt/Resources/Raw/app.js').read_text()
        assert (ROOT/'BrowserPreview/style.css').read_text()==(ROOT/'WhiskerHunt/Resources/Raw/style.css').read_text()
        assert "const CACHE='whisker-hunt-shell-v22'" in (ROOT/'BrowserPreview/sw.js').read_text()
        assert not errors,errors
        print('PASS v1.6: live aim guide, green release, minimum drag, miss, lure, ball, saved cat/XP, synced native assets')
        await browser.close()

if __name__=='__main__': asyncio.run(main())
