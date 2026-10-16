"""v1.4 regression: actual visible-photo coordinates for portrait/landscape shots.
Run with: python3 tests/test_v14.py (requires Pillow and Playwright Chromium).
"""
import asyncio, base64, io
from pathlib import Path
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(width,height):
    img=Image.new('RGB',(width,height),'#ddd')
    draw=ImageDraw.Draw(img)
    draw.rectangle((0,0,width//2,height),fill='#ff2828')
    draw.rectangle((width//2,0,width,height),fill='#2244ee')
    out=io.BytesIO();img.save(out,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844},has_touch=True)
        errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
        html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
        await page.evaluate('''() => {window.__cats=new Map();window.__meta=new Map();
          window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value);}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
          window.transact=async (store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete'){m.delete(value);return}};boot();}''')
        await page.wait_for_function('window.whiskerBootComplete')

        async def open_photo(w,h):
            await page.evaluate('(image)=>beginEncounter(image)',photo(w,h))
            await page.locator('#encounter-stage').wait_for()
            await page.wait_for_function('document.getElementById("encounter-photo").naturalWidth>0')
            await page.wait_for_function('document.getElementById("encounter-cat-crop").src.startsWith("data:image/jpeg")')

        async def click_photo_at(x,y):
            loc=await page.evaluate('''() => {
                const img=document.getElementById('encounter-photo');
                return encounterImageRect(img,img.getBoundingClientRect());
            }''')
            cx=loc['left']+loc['width']*x;cy=loc['top']+loc['height']*y
            await page.mouse.click(cx,cy)
            await page.wait_for_timeout(400)
            focus=await page.evaluate('s.encounterFocus')
            assert abs(focus['x']-x)<.01 and abs(focus['y']-y)<.01,(focus,x,y)
            rect=await page.locator('#encounter-cat').bounding_box()
            tx=rect['x']+rect['width']/2;ty=rect['y']+rect['height']/2
            # CSS transitions and ring scaling do not change the centre of the target.
            assert abs(tx-cx)<2.5 and abs(ty-cy)<2.5, (tx,ty,cx,cy)

        async def click_letterbox():
            bounds=await page.locator('#encounter-photo').bounding_box()
            photo_rect=await page.evaluate('''() => {const img=document.getElementById('encounter-photo');return encounterImageRect(img,img.getBoundingClientRect())}''')
            previous=await page.evaluate('s.encounterFocus')
            if photo_rect['width']<bounds['width']-5:
                cx=bounds['x']+5;cy=bounds['y']+bounds['height']/2
            else:
                cx=bounds['x']+bounds['width']/2;cy=bounds['y']+5
            await page.mouse.click(cx,cy)
            assert await page.evaluate('s.encounterFocus')==previous, 'Tap on letterbox margin incorrectly moved cat'

        await open_photo(300,600)
        await click_photo_at(.78,.36)
        await click_letterbox()
        await click_photo_at(.21,.44)
        # Rapid successive crop requests must end with the latest focus (red half).
        await page.evaluate('''() => {setEncounterFocus(.80,.40);setEncounterFocus(.20,.40)}''')
        await page.wait_for_timeout(250)
        rgb=await page.evaluate('''async () => {
            const img=document.getElementById('encounter-cat-crop');await img.decode();
            const c=document.createElement('canvas');c.width=c.height=1;
            const ctx=c.getContext('2d');ctx.drawImage(img,0,0,1,1);
            return [...ctx.getImageData(0,0,1,1).data].slice(0,3);
        }''')
        assert rgb[0]>rgb[2]*1.5, ('Stale crop overwrote latest red selection',rgb)
        # Resize the stage: the target must continue tracking the photo coordinates.
        await page.evaluate("document.getElementById('encounter-stage').style.width='280px'")
        await page.wait_for_timeout(350)
        await click_photo_at(.74,.40)
        await page.screenshot(path=str(ROOT/'tests/v14-portrait-alignment.png'),full_page=True)

        # Test wide landscape shots (top/bottom letterboxing).
        await open_photo(600,300)
        await click_photo_at(.62,.42)
        await click_letterbox()
        await click_photo_at(.30,.58)
        # The capture loop and original CatDex save must still work.
        await page.locator('#tool-lure').click()
        await page.evaluate('handleEncounterHit("lure")')
        assert await page.evaluate('s.encounterLured')
        await page.evaluate('handleEncounterHit("ball")')
        await page.locator('#encounter-continue').wait_for()
        await page.locator('#encounter-continue').click()
        await page.locator('#cat-name').fill('Letterbox')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.get_by_text('Letterbox',exact=True).first.wait_for()
        assert await page.evaluate('s.cats.length')==1
        assert await page.evaluate('s.cats[0].sightings.length')==1
        assert await page.evaluate('s.profile.xp')>=100
        assert (ROOT/'BrowserPreview/app.js').read_text()==(ROOT/'WhiskerHunt/Resources/Raw/app.js').read_text()
        assert (ROOT/'BrowserPreview/style.css').read_text()==(ROOT/'WhiskerHunt/Resources/Raw/style.css').read_text()
        assert not errors,errors
        print('PASS v1.4: portrait/landscape focus mapping, letterbox rejection, resize, latest crop, capture, CatDex save, synced assets')
        await browser.close()

if __name__=='__main__': asyncio.run(main())
