"""v2.1 live retake + paw-shaped pod polish."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT = Path(__file__).resolve().parents[1]

def photo(rgb=(120,90,180)):
    im = Image.new("RGB", (240, 320), rgb)
    buf = io.BytesIO()
    im.save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

async def main():
    app_js = (ROOT / 'BrowserPreview/app.js').read_text()
    css = (ROOT / 'BrowserPreview/style.css').read_text()
    assert 'LIVE_FRAME_MAX=4' in app_js
    assert 'LIVE_SAMPLE_INTERVAL=900' in app_js
    assert "width:{ideal:800}" in app_js and 'frameRate:{ideal:20,max:24}' in app_js
    assert '🎥 Retake live capture' in app_js
    assert 'Paw grab…' in app_js and 'Holding on…' in app_js
    assert '.paw-pod' in css and 'border-radius:50%' in css
    assert 'whisker-hunt-shell-v22' in (ROOT / 'BrowserPreview/sw.js').read_text()
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width': 390, 'height': 844})
        html = (ROOT / 'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>', '').replace('<link rel="stylesheet" href="style.css">', '')
        await page.set_content(html)
        await page.add_style_tag(content=css)
        await page.add_script_tag(content=app_js)
        await page.evaluate("""() => {
            window.__cats = new Map();
            window.__meta = new Map();
            window.openDb = async () => ({ mock:true, transaction:()=>({ objectStore:()=>({ put:()=>{} }) }) });
            window.transact = async (store, mode, method, value) => {
                const m = store === 'cats' ? window.__cats : window.__meta;
                if (method === 'getAll') return Array.from(m.values());
                if (method === 'get') return m.get(value);
                if (method === 'put') { m.set(store === 'cats' ? value.id : value.key, value); return value; }
                if (method === 'delete') { m.delete(value); return; }
            };
            boot();
        }""")
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.evaluate('(im)=>showEncounter(im,{label:"Usable",note:"ok"},{live:true})', photo())
        await page.locator('#encounter-stage').wait_for()
        label = await page.locator('#encounter-retake').text_content()
        assert 'Retake live capture' in label
        radii = await page.evaluate("""() => ({
            pod: getComputedStyle(document.getElementById('tool-ball')).borderRadius,
            lure: getComputedStyle(document.getElementById('tool-lure')).borderRadius
        })""")
        assert radii['pod'] == radii['lure']
        count = await page.evaluate("""() => {
            window.__retakeCalls = 0;
            startLiveEncounter = () => { window.__retakeCalls += 1; };
            document.getElementById('encounter-retake').click();
            return window.__retakeCalls;
        }""")
        assert count == 1
        await page.evaluate('(im)=>showEncounter(im,{label:"Usable",note:"ok"},{live:false})', photo((90,120,160)))
        await page.locator('#encounter-stage').wait_for()
        await page.evaluate('handleEncounterHit("ball",0.2)')
        await page.wait_for_timeout(350)
        mid = await page.locator('#encounter-status').text_content()
        assert 'Paw grab' in mid or 'Holding on' in mid
        print('PASSED v2.1: paw-shaped/circular live UI, live retake hook, paw capture messaging, lighter live constants')
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
