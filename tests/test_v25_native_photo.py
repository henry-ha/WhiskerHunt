"""v2.5: Android photo-picker token race, cancellation, versioning and data safety.

Runs browser interaction with a stubbed native URL bridge; no APK or camera is compiled.
"""
import asyncio
import base64
import io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


def image_uri(rgb):
    image = Image.new('RGB', (640, 900), rgb)
    out = io.BytesIO()
    image.save(out, format='JPEG', quality=92)
    return 'data:image/jpeg;base64,' + base64.b64encode(out.getvalue()).decode()


async def main():
    js = (ROOT / 'BrowserPreview/app.js').read_text()
    raw_js = (ROOT / 'WhiskerHunt/Resources/Raw/app.js').read_text()
    assert js == raw_js, 'Browser preview and bundled MAUI JavaScript differ'
    bridge_call = "location.href=(capture?'whiskerhunt://capture':'whiskerhunt://import')+'?request='+encodeURIComponent(token);"
    assert bridge_call in js
    # Intercept the custom-scheme navigation only in this test harness.
    js = js.replace(bridge_call, "window.__bridgeRequests.push((capture?'capture':'import')+':'+token);")
    cs = (ROOT / 'WhiskerHunt/MainPage.xaml.cs').read_text()
    assert 'GetPhotoAsync(true, GetQuery(request, "request"))' in cs
    assert 'GetPhotoAsync(false, GetQuery(request, "request"))' in cs
    assert 'window.whiskerNativePhoto({JsonSerializer.Serialize(dataUri)},{JsonSerializer.Serialize(requestToken)})' in cs
    assert 'window.whiskerNativePhotoCancelled?.({JsonSerializer.Serialize(requestToken)})' in cs
    assert cs.count('await ReportPhotoCancelledAsync(requestToken)') >= 4
    project = (ROOT / 'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationDisplayVersion>2.5.0</ApplicationDisplayVersion>' in project
    assert '<ApplicationVersion>25</ApplicationVersion>' in project
    assert 'whisker-hunt-shell-v25' in (ROOT / 'BrowserPreview/sw.js').read_text()
    assert "const DATABASE='whiskerhunt_local_v1', DB_VERSION=1;" in js

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width': 390, 'height': 844})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        html = (ROOT / 'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>', '').replace('<link rel="stylesheet" href="style.css">', '')
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT / 'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=js)
        await page.evaluate('''() => {
          window.__cats = new Map(); window.__meta = new Map();
          window.__bridgeRequests = [];
          window.openDb = async () => ({ mock: true, transaction: () => ({ objectStore: () => ({ put: () => {} }) }) });
          window.transact = async (store, mode, method, value) => {
            const m = store === 'cats' ? window.__cats : window.__meta;
            if (method === 'getAll') return Array.from(m.values());
            if (method === 'get') return m.get(value);
            if (method === 'put') { m.set(store === 'cats' ? value.id : value.key, value); return value; }
            if (method === 'delete') { m.delete(value); return; }
          };
          boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.evaluate('window.whiskerNativeReady=true')
        initial = await page.evaluate('({cats:s.cats.length,xp:s.profile.xp})')
        assert initial == {'cats': 0, 'xp': 0}

        # Request 1: user leaves before Android returns the photo.
        await page.evaluate('requestEncounterPhoto(true)')
        token1 = (await page.evaluate('__bridgeRequests[0]')).split(':')[1]
        await page.evaluate('closeModal()')
        await page.evaluate('(args)=>whiskerNativePhoto(args.image,args.token)', {'image': image_uri((220, 30, 30)), 'token': token1})
        await page.wait_for_timeout(100)
        state = await page.evaluate('({visible:!document.getElementById("modal-layer").classList.contains("hidden"),image:s.image})')
        assert not state['visible'] and not state['image'], f'Stale Android photo reopened dismissed UI: {state}'

        # Request 2 followed by request 3: out-of-order callbacks must not replace request 3.
        await page.evaluate('requestEncounterPhoto(true)')
        token2 = (await page.evaluate('__bridgeRequests[1]')).split(':')[1]
        await page.evaluate('requestEncounterPhoto(false)')
        token3 = (await page.evaluate('__bridgeRequests[2]')).split(':')[1]
        assert token2 != token3
        await page.evaluate('(args)=>whiskerNativePhoto(args.image,args.token)', {'image': image_uri((30, 220, 30)), 'token': token2})
        await page.wait_for_timeout(100)
        assert not await page.evaluate('Boolean(s.image)'), 'Old camera photo replaced newer gallery selection'
        await page.evaluate('(args)=>whiskerNativePhoto(args.image,args.token)', {'image': image_uri((30, 30, 220)), 'token': token3})
        await page.locator('#encounter-stage').wait_for(timeout=8000)
        assert await page.evaluate('s.image.startsWith("data:image/jpeg;base64,")')
        assert await page.evaluate('nativePhotoRequestToken===null')
        assert await page.evaluate('s.captureSummary.quality.width>=640')

        # Cancelling a picker keeps the existing encounter and its selected photo.
        old_image = await page.evaluate('s.image')
        await page.evaluate('requestEncounterPhoto(true)')
        token4 = (await page.evaluate('__bridgeRequests[3]')).split(':')[1]
        await page.evaluate('(token)=>whiskerNativePhotoCancelled(token)', token4)
        assert await page.evaluate('nativePhotoRequestToken===null')
        assert await page.evaluate('s.image') == old_image
        assert 'Photo cancelled' in await page.locator('#encounter-status').text_content()
        # A delayed callback from the cancelled picker is also ignored.
        await page.evaluate('(args)=>whiskerNativePhoto(args.image,args.token)', {'image': image_uri((250, 200, 30)), 'token': token4})
        await page.wait_for_timeout(80)
        assert await page.evaluate('s.image') == old_image

        # No CatDex writes, XP changes or backup-schema changes during picker handling.
        final = await page.evaluate('''() => ({cats:s.cats.length,xp:s.profile.xp,backupVersion:backupPayload().version,
          database:DATABASE,dbVersion:DB_VERSION})''')
        assert final == {'cats': 0, 'xp': 0, 'backupVersion': 1, 'database': 'whiskerhunt_local_v1', 'dbVersion': 1}, final
        assert not errors, errors
        await browser.close()
    print('PASS v2.5: native picker tokens, close/cancel/out-of-order protection, photo quality, unchanged CatDex and backup schema, Android version bump')


if __name__ == '__main__':
    asyncio.run(main())
