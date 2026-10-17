"""v3.2.0 UI regression: active live tool is hidden and paw art looks cat-like."""
import asyncio, base64, io, re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(rgb=(190,140,95)):
    im=Image.new('RGB',(240,320),rgb); out=io.BytesIO(); im.save(out,format='JPEG')
    return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
    assert 'Source="index_v34.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    cs=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationDisplayVersion>3.2.0</ApplicationDisplayVersion>' in cs
    assert '<ApplicationVersion>34</ApplicationVersion>' in cs
    source=(ROOT/'BrowserPreview/app.js').read_text()
    assert "const WHISKER_BUILD='3.2.0'" in source
    assert "cleaner live tool switcher" in source
    assert (ROOT/'WhiskerHunt/Resources/Raw/app_v34.js').read_text()==source
    assert (ROOT/'WhiskerHunt/Resources/Raw/style_v34.css').read_text()==(ROOT/'BrowserPreview/style.css').read_text()
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[]; page.on('pageerror', lambda e: errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text()
        html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
        html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=source)
        await page.evaluate('''() => {
          window.__cats=new Map();window.__meta=new Map();
          window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value);}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
          window.transact=async (store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete'){m.delete(value);return}};
          boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.evaluate('(im)=>showEncounter(im,{score:80,label:"Clear-looking",note:"Good"},{live:false})', photo())
        await page.wait_for_selector('#encounter-stage')
        assert await page.locator('#tool-ball').is_hidden()
        assert await page.locator('#tool-lure').is_visible()
        claw_count=await page.evaluate('document.querySelectorAll(".whisker-paw-svg .paw-claw").length')
        assert claw_count >= 4
        await page.locator('#tool-lure').click()
        await page.wait_for_function('document.querySelector("#throw-item").classList.contains("throw-lure")')
        assert await page.locator('#tool-lure').is_hidden()
        assert await page.locator('#tool-ball').is_visible()
        aria=await page.locator('#throw-item').get_attribute('aria-label')
        assert 'Dangle Lure' in aria
        await page.evaluate('handleEncounterHit("lure")')
        await page.wait_for_function('document.querySelector("#throw-item").classList.contains("throw-ball")')
        assert await page.locator('#tool-ball').is_hidden()
        assert await page.locator('#tool-lure').is_visible()
        status=await page.locator('#encounter-status').text_content()
        assert 'Whisker Paw' in status or 'capture' in status
        assert not errors, errors
        print('PASS v3.2.0: active tool hidden, alternative tool shown, cat-claw paw art present')
        await browser.close()

if __name__=='__main__':
    asyncio.run(main())
