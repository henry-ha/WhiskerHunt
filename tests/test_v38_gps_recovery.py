"""v3.6 browser integration for native location response, failure reasons and CatDex pins."""
import asyncio, base64, io, re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
    im=Image.new('RGB',(240,320),(160,128,96))
    out=io.BytesIO();im.save(out,format='JPEG')
    return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
    project=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationDisplayVersion>3.6.0</ApplicationDisplayVersion>' in project
    assert '<ApplicationVersion>38</ApplicationVersion>' in project
    assert 'Source="index_v38.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    native=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
    assert 'GetLastKnownLocationAsync' in native
    assert 'GeolocationAccuracy.Low' in native
    assert 'AccessCoarseLocation' in native
    assert 'case NativeLocationSettingsHost' in native
    assert 'window.whiskerNativeLocationError?.({safeToken},{JsonSerializer.Serialize(reason)})' in native
    source=(ROOT/'BrowserPreview/app.js').read_text()
    route="location.href='whiskerhunt://location?request='+encodeURIComponent(token)"
    assert route in source
    mock_source=source.replace(route, 'window.__nativeGpsRequests.push(token)')
    for folder in [ROOT/'BrowserPreview',ROOT/'WhiskerHunt/Resources/Raw']:
        assert (folder/'app.js').read_text()==source
        assert (folder/'app_v38.js').read_text()==source
        assert 'app_v38.js' in (folder/'index_v38.html').read_text()
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text()
        html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
        html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=mock_source)
        await page.evaluate('''() => {
            window.__cats=new Map();window.__meta=new Map(); window.__nativeGpsRequests=[];
            window.openDb=async()=>({mock:true,transaction:()=>{const tx={objectStore:(store)=>({put:(value)=>{(store==='cats'?window.__cats:window.__meta).set(store==='cats'?value.id:value.key,value)}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
            window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete'){m.delete(value);return}};
            boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.evaluate('window.whiskerAndroidShell=true; window.whiskerNativeReady=true;')
        # Do not need a real phone; exercise original bridge handler with a simulated Android callback.
        await page.evaluate('''(im)=>{
           s.arModelKey=AR_CAT_MODELS[0].key; s.arHabitatKey=AR_HABITATS[0].key;
           s.encounterAr=true;s.encounterCaptured=true;s.image=im;s.encounterFocus={x:.55,y:.7};
           showVirtualNamingForm();
        }''',photo())
        await page.locator('#virtual-pin').check()
        assert await page.locator('#virtual-pin-helper').is_visible()
        await page.locator('#virtual-pin-allow').click()
        await page.wait_for_function('window.__nativeGpsRequests.length===1')
        token=await page.evaluate('window.__nativeGpsRequests[0]')
        await page.evaluate('''token=>window.whiskerNativeLocationError(token,'no_fix')''',token)
        assert await page.locator('#virtual-pin-failure').is_visible()
        assert 'no usable position' in (await page.locator('#virtual-pin-failure').text_content()).lower()
        assert await page.locator('#virtual-pin-device-location').is_visible()
        # App shell flag is sufficient to open settings; no browser-only generic fallback.
        native_settings=await page.evaluate("""() => window.openLocationSettings.toString().includes('window.whiskerAndroidShell')""")
        assert native_settings
        await page.locator('#virtual-pin-retry').click()
        await page.wait_for_function('window.__nativeGpsRequests.length===2')
        token2=await page.evaluate('window.__nativeGpsRequests[1]')
        await page.evaluate('''(token)=>window.whiskerNativeLocation(51.5429,-.12582,token)''',token2)
        await page.wait_for_function('s.pendingApproxLocation!==null')
        assert await page.locator('#virtual-pin-failure').is_hidden()
        loc=await page.evaluate('s.pendingApproxLocation')
        assert loc=={'lat':51.54,'lng':-.13},loc
        await page.locator('#virtual-save-final').click()
        await page.wait_for_function('s.cats.length===1')
        snapshot=await page.evaluate('''() => ({cat:s.cats[0],map:renderExplore(),full:backupPayload(),safe:backupPayload(true)})''')
        v=snapshot['cat']['sightings'][0]
        assert (v['lat'],v['lng'])==(51.54,-.13)
        assert 'Saved locations (1)' in snapshot['map']
        assert snapshot['full']['cats'][0]['sightings'][0]['lat']==51.54
        assert 'lat' not in snapshot['safe']['cats'][0]['sightings'][0]
        # A fresh, unrelated catch must not silently inherit the previous marker.
        assert await page.evaluate('s.pendingApproxLocation===null')
        # Older callback arriving after a later GPS request must remain ignored.
        race=await page.evaluate('''async () => {
          window.__nativeGpsRequests=[];
          const first=locationPrompt(), second=locationPrompt();
          const a=window.__nativeGpsRequests[0], b=window.__nativeGpsRequests[1];
          const cancelled=await first;
          window.whiskerNativeLocation(90,90,a);
          const waiting=activeLocationFinish!==null;
          window.whiskerNativeLocation(50.98765,-.1234,b);
          return {cancelled,waiting,second:await second};
        }''')
        assert race=={'cancelled':None,'waiting':True,'second':{'lat':50.99,'lng':-.12}},race
        assert not errors,errors
        await browser.close()
        print('PASS v3.6: typed GPS failure, retry success, rounded private map pin and GPS-free backup')
if __name__=='__main__': asyncio.run(main())
