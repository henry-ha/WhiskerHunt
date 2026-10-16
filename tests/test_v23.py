"""v2.3: live retake state + selection prevention + paw-only pod styling."""
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
    assert 's.encounterLive=true;' in js
    assert "$('encounter-retake').onclick=()=>s.encounterLive?startLiveEncounter():requestEncounterPhoto(true);" in js
    assert '-webkit-touch-callout:none!important' in css
    assert 'throw-item.throw-ball,.throw-item.throw-ball:before,.throw-item.throw-ball:after{background:none!important;border:0!important;box-shadow:none!important;outline:none!important}' in css
    assert 'whisker-hunt-shell-v23' in (ROOT/'BrowserPreview/sw.js').read_text()
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
        await page.evaluate('(im)=>showEncounter(im,{label:"Usable",note:"ok"},{live:true})', photo())
        await page.locator('#encounter-stage').wait_for()
        txt=await page.locator('#encounter-retake').text_content()
        assert 'Retake live capture' in txt
        rad=await page.evaluate("""() => ({ tool:getComputedStyle(document.getElementById('tool-ball')).borderRadius, select:getComputedStyle(document.getElementById('tool-ball')).userSelect, throwBg:getComputedStyle(document.getElementById('throw-item')).backgroundImage, throwRadius:getComputedStyle(document.getElementById('throw-item')).borderRadius })""")
        assert rad['select'] == 'none'
        assert rad['throwRadius'] in ('0px','0') or rad['throwRadius'].startswith('0')
        count=await page.evaluate("""() => { window.__retakeCalls=0; startLiveEncounter=()=>{window.__retakeCalls += 1;}; document.getElementById('encounter-retake').click(); return window.__retakeCalls; }""")
        assert count == 1
        print('PASSED v2.3: live retake state, selection prevention, paw-only pod styling, cache version')
        await browser.close()

if __name__=='__main__':
    asyncio.run(main())
