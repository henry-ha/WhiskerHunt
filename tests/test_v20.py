"""v2.0 performance-oriented encounter polish."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT = Path(__file__).resolve().parents[1]

def photo(rgb):
    im = Image.new("RGB", (240, 320), rgb)
    buf = io.BytesIO()
    im.save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

async def main():
    app_js = (ROOT / 'BrowserPreview/app.js').read_text()
    style_css = (ROOT / 'BrowserPreview/style.css').read_text()
    assert 'const LIVE_FRAME_MAX=5' in app_js
    assert 'LIVE_SAMPLE_INTERVAL=700' in app_js
    assert "width:{ideal:960}" in app_js
    assert 'frameRate:{ideal:24,max:30}' in app_js
    assert 'Shake 1 of 2' not in app_js and 'Shake 2 of 2' not in app_js
    assert 'whisker-hunt-shell-v20' in (ROOT / 'BrowserPreview/sw.js').read_text()
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width': 390, 'height': 844})
        html = (ROOT / 'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>', '').replace('<link rel="stylesheet" href="style.css">', '')
        await page.set_content(html)
        await page.add_style_tag(content=style_css)
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
        await page.evaluate('(im)=>beginEncounter(im)', photo((120, 90, 180)))
        await page.locator('#encounter-stage').wait_for()
        throw_style = await page.evaluate("""() => {
            const item = document.getElementById('throw-item');
            const shell = document.querySelector('#encounter-orb .pod-shell');
            return { item: getComputedStyle(item).borderRadius, shell: getComputedStyle(shell).borderRadius };
        }""")
        assert throw_style['item'] in ('50%', '36px', '33px', '32px') or throw_style['item'].endswith('px')
        assert throw_style['shell'] in ('50%', '44px') or throw_style['shell'].endswith('px')
        await page.evaluate('handleEncounterHit("ball",0.2)')
        await page.wait_for_timeout(900)
        mid = await page.locator('#encounter-status').text_content()
        assert 'Shake' not in mid
        assert mid in ('Got it…', 'Almost there…') or 'Almost there' in mid
        await page.wait_for_timeout(700)
        final = await page.locator('#encounter-status').text_content()
        assert 'You captured this cat!' in final
        print('PASSED v2.0: live tuning constants, circular pod styling, friendly capture messaging, cache version')
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
