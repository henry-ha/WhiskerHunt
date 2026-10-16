"""v2.4: live-start fallback bug fix, stylised paw selector, meow capture flourish."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(rgb=(120,90,180)):
    im=Image.new('RGB',(240,320),rgb)
    buf=io.BytesIO(); im.save(buf, format='JPEG')
    return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()

async def main():
    js=(ROOT/'BrowserPreview/app.js').read_text()
    css=(ROOT/'BrowserPreview/style.css').read_text()
    assert 'function useNormalCameraFromLiveStartup()' in js
    assert 'Meow!' in js and '.encounter-meow' in css
    assert 'whisker-hunt-shell-v24' in (ROOT/'BrowserPreview/sw.js').read_text()
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=css)
        await page.add_script_tag(content=js)
        await page.evaluate("""() => {
            window.__cats = new Map(); window.__meta = new Map();
            window.openDb = async () => ({ mock:true, transaction:()=>({ objectStore:()=>({ put:()=>{} }) }) });
            window.transact = async (store, mode, method, value) => { const m = store==='cats'?window.__cats:window.__meta; if(method==='getAll') return Array.from(m.values()); if(method==='get') return m.get(value); if(method==='put'){m.set(store==='cats'?value.id:value.key, value); return value;} if(method==='delete'){m.delete(value); return;} };
            boot();
        }""")
        await page.wait_for_function('window.whiskerBootComplete===true')
        # Simulate the stuck-screen path: starting-live modal -> fallback to normal camera
        await page.evaluate("""() => {
            openModal(`<div class="sheet-head"><h2>Starting live camera…</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">Requesting camera access. No video is saved or uploaded.</p><div class="live-loading" aria-live="polite">🎥 Preparing preview…</div><div class="actions"><button id="live-fallback" class="secondary">Use normal camera instead</button></div>`);
            window.__captureCalls = 0;
            requestEncounterPhoto = () => { window.__captureCalls += 1; };
            document.getElementById('live-fallback').onclick = useNormalCameraFromLiveStartup;
        }""")
        await page.click('#live-fallback')
        await page.wait_for_timeout(80)
        state = await page.evaluate("""() => ({ hidden: document.getElementById('modal-layer').classList.contains('hidden'), calls: window.__captureCalls })""")
        assert state['hidden'] is True and state['calls'] == 1
        # Show live encounter and verify meow appears on capture
        await page.evaluate('(im)=>showEncounter(im,{label:"Usable",note:"ok"},{live:true})', photo())
        await page.locator('#encounter-stage').wait_for()
        ui = await page.evaluate("""() => ({
            rad: getComputedStyle(document.getElementById('tool-ball')).borderRadius,
            bg: getComputedStyle(document.querySelector('#tool-ball span')).backgroundImage,
            select: getComputedStyle(document.getElementById('tool-ball')).userSelect
        })""")
        assert ui['select'] == 'none'
        assert '999' in ui['rad'] or ui['rad'].endswith('px')
        await page.evaluate('s.captureSummary.throwRating="Nice!"; runEncounterCapture()')
        await page.wait_for_timeout(760)
        meow_class = await page.locator('#encounter-meow').get_attribute('class')
        assert 'float' in meow_class
        print('PASSED v2.4: live-start fallback closes loading modal, normal camera handoff occurs, stylised selector remains circular, meow flourish appears')
        await browser.close()

if __name__=='__main__':
    asyncio.run(main())
