"""v3.1.1 camera startup smoke with a mocked MediaStream."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'],headless=True)
        page=await b.new_page(viewport={'width':390,'height':844})
        page_errors=[]; page.on('pageerror',lambda e:page_errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index_v32.html').read_text().replace('<script src="app_v32.js" defer></script>','').replace('<link rel="stylesheet" href="style_v32.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style_v32.css').read_text())
        await page.add_script_tag(content=(ROOT/'BrowserPreview/app_v32.js').read_text())
        await page.evaluate('''() => {
            window.openDb=async()=>({});window.transact=async()=>[];boot();
            const c=document.createElement('canvas');c.width=640;c.height=480;
            const ctx=c.getContext('2d');ctx.fillStyle='#837a91';ctx.fillRect(0,0,640,480);
            ctx.fillStyle='#fbe3c1';ctx.fillRect(40,120,560,250);
            window.__fakeStream=c.captureStream(20);
            Object.defineProperty(window,'isSecureContext',{configurable:true,get:()=>true});
            Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>window.__fakeStream}});
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.evaluate('startArEncounter()')
        await page.locator('#encounter-ar-cat').wait_for(timeout=13000)
        assert 'AR safari' in await page.locator('.sheet-head').inner_text()
        assert 'build 32' in await page.locator('.whisker-build-stamp').inner_text()
        assert await page.locator('#encounter-video').count()==1
        assert not page_errors,page_errors
        await page.locator('[data-close]').first.click()
        assert await page.evaluate('liveCamera===null')
        print('PASS: mocked real MediaStream opens AR Safari without crash or fallback, stops on close')
        await b.close()
if __name__=='__main__':asyncio.run(main())
