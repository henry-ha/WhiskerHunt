"""v1.7 encounter UI: Whisker Pod and in-preview tool dock."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT = Path(__file__).resolve().parents[1]

def photo(rgb):
    im = Image.new("RGB", (200, 320), rgb)
    buf = io.BytesIO()
    im.save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width': 390, 'height': 844})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        html = (ROOT / 'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>', '').replace('<link rel="stylesheet" href="style.css">', '')
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT / 'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=(ROOT / 'BrowserPreview/app.js').read_text())
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
        im = photo((90, 120, 180))
        await page.evaluate('(im)=>beginEncounter(im)', im)
        await page.locator('#encounter-stage').wait_for()
        assert await page.locator('.encounter-tool-dock').count() == 1
        assert await page.get_by_text('Pod', exact=True).count() >= 1
        assert await page.get_by_text('Lure', exact=True).count() >= 1
        assert await page.locator('.encounter-tools').count() == 0
        assert await page.locator('#throw-item.throw-ball').count() == 1
        txt = await page.locator('#encounter-status').text_content()
        assert 'tool dock on the right' in txt
        await page.locator('#tool-lure').click()
        assert await page.locator('#tool-lure').get_attribute('aria-pressed') == 'true'
        assert await page.evaluate('encounterToolLabel("ball")') == 'Whisker Pod'
        await page.evaluate('handleEncounterHit("lure")')
        await page.evaluate('handleEncounterHit("ball",0.2)')
        await page.locator('#encounter-continue').wait_for()
        assert await page.get_by_text('Whisker Pod', exact=False).count() >= 1
        assert 'whisker-hunt-shell-v22' in (ROOT / 'BrowserPreview/sw.js').read_text()
        assert not errors, errors
        print('PASSED v1.7: Whisker Pod UI, in-preview dock, capture summary, v17 cache')
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
