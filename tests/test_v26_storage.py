"""Real Chromium IndexedDB reload test (not mocked, not Android native)."""
import asyncio
import base64
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

async def main():
    handler=functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT/'BrowserPreview'))
    server=ThreadingHTTPServer(('127.0.0.1',0),handler)
    worker=Thread(target=server.serve_forever,daemon=True)
    worker.start()
    try:
        async with async_playwright() as p:
            browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=await browser.new_page()
            url=f'http://127.0.0.1:{server.server_port}/'
            await page.goto(url)
            await page.wait_for_function('window.whiskerBootComplete===true')
            assert await page.evaluate('Boolean(s.db)')
            photo='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
            await page.evaluate('''async (photo) => {
                const cat={id:'v26-storage-test',name:'Storage Kitty',coat:'Tabby',personality:'Curious',note:'persist',photo,signature:'test',createdAt:'2026-10-16T10:00:00.000Z',fav:true,
                    sightings:[{id:'v26-sighting',at:'2026-10-16T10:00:00.000Z',photo,note:'hello'}]};
                await transact('cats','readwrite','put',cat);
                await transact('meta','readwrite','put',{key:'profile',value:{name:'Cat Explorer',xp:320,claimed:['test-quest']}});
            }''',photo)
            await page.reload()
            await page.wait_for_function('window.whiskerBootComplete===true')
            state=await page.evaluate('''() => ({cats:s.cats.length,photo:s.cats[0]?.photo, sighting:s.cats[0]?.sightings?.[0]?.id,xp:s.profile.xp,claimed:s.profile.claimed,backupVersion:backupPayload().version,database:DATABASE})''')
            assert state=={'cats':1,'photo':photo,'sighting':'v26-sighting','xp':320,'claimed':['test-quest'],'backupVersion':1,'database':'whiskerhunt_local_v1'},state
            await browser.close()
            print('PASS v2.6: real IndexedDB survives reload with cat photo, sighting, XP, quest claim and backup v1')
    finally:
        server.shutdown();server.server_close()

if __name__=='__main__':asyncio.run(main())
