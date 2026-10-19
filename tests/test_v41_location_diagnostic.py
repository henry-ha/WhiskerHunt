"""v3.7.2: Coarse-only Android permission source plus live UI diagnostics and location save regression.

Browser integration simulates native callback; Android SDK compilation requires a Windows/MAUI build machine.
"""
from pathlib import Path
import re, asyncio, io, base64
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
    im=Image.new('RGB',(240,320),(142,122,105));buf=io.BytesIO()
    im.save(buf,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()

async def main():
    csharp=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
    coarse=(ROOT/'WhiskerHunt/Platforms/Android/WhiskerCoarseLocationPermission.cs').read_text()
    provider=(ROOT/'WhiskerHunt/Platforms/Android/AndroidApproximateLocationProvider.cs').read_text()
    assert 'AccessCoarseLocation, true' in coarse
    assert 'Permissions.BasePlatformPermission' in coarse
    assert 'RequestAsync<WhiskerCoarseLocationPermission>()' in csharp
    assert 'RequestAsync<Permissions.LocationWhenInUse>()' not in csharp[csharp.index('private async Task GetLocationAsync'):csharp.index('// Safety gate: reject')].split('#else')[0]
    assert 'case "location-check"' in csharp
    assert 'whiskerNativeLocationDiagnostic?.(' in csharp
    assert 'TryGetAsync(TimeSpan.FromSeconds(18))' in csharp
    assert 'RequestSingleUpdate' in provider
    assert 'ACCESS_COARSE_LOCATION' in (ROOT/'WhiskerHunt/Platforms/Android/AndroidManifest.xml').read_text()
    assert '<ApplicationDisplayVersion>3.7.2</ApplicationDisplayVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationVersion>41</ApplicationVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert 'Source="index_v41.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    src=(ROOT/'BrowserPreview/app.js').read_text()
    for folder in [ROOT/'BrowserPreview',ROOT/'WhiskerHunt/Resources/Raw']:
        assert (folder/'app_v41.js').read_text()==src
        assert 'app_v41.js' in (folder/'index_v41.html').read_text()
        assert 'style_v41.css' in (folder/'index_v41.html').read_text()
        assert 'whisker-hunt-shell-v41' in (folder/'sw.js').read_text()
    route="location.href='whiskerhunt://location?request='+encodeURIComponent(token)"
    diagnostic_route="location.href='whiskerhunt://location-check?request='+encodeURIComponent(token)"
    assert route in src and diagnostic_route in src
    mocked=src.replace(route,'window.__nativeRequests.push(token)').replace(diagnostic_route,'window.__checkRequests.push(token)')
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text()
        html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
        html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=mocked)
        await page.evaluate('''() => {
          window.__cats=new Map();window.__meta=new Map();window.__nativeRequests=[];window.__checkRequests=[];
          window.openDb=async()=>({mock:true,transaction:()=>{const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value)}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
          window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete'){m.delete(value);return}};
          boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.evaluate('window.whiskerAndroidShell=true;window.whiskerNativeReady=true')
        await page.evaluate('''im=>{s.arModelKey=AR_CAT_MODELS[0].key;s.arHabitatKey=AR_HABITATS[0].key;s.encounterAr=true;s.encounterCaptured=true;s.image=im;s.encounterFocus={x:.5,y:.69};showVirtualNamingForm()}''',photo())
        await page.locator('#virtual-pin').check()
        assert await page.locator('#virtual-pin-check').is_visible()
        await page.locator('#virtual-pin-allow').click()
        await page.wait_for_function('window.__nativeRequests.length===1')
        token=await page.evaluate('window.__nativeRequests[0]')
        await page.evaluate('(token)=>window.whiskerNativeLocationError(token,"permission")',token)
        await page.wait_for_function('window.__checkRequests.length===1')
        check_token=await page.evaluate('window.__checkRequests[0]')
        await page.evaluate('''token=>window.whiskerNativeLocationDiagnostic(token,{build:"3.7.2",coarse:true,fine:false,deviceEnabled:true})''',check_token)
        msg=await page.locator('#virtual-pin-diagnostics').inner_text()
        assert 'Approximate: allowed' in msg and 'Precise: not granted' in msg and 'Phone Location: on' in msg, msg
        assert '51.' not in msg  # no geographic coordinates
        # Retry: the resulting private pin actually saves to CatDex, and safe backup removes it.
        await page.locator('#virtual-pin-retry').click()
        await page.wait_for_function('window.__nativeRequests.length===2')
        second=await page.evaluate('window.__nativeRequests[1]')
        await page.evaluate('token=>window.whiskerNativeLocation(51.5381,-.1239,token)',second)
        await page.wait_for_function('s.pendingApproxLocation !== null')
        await page.locator('#virtual-save-final').click()
        await page.wait_for_function('s.cats.length===1')
        saved=await page.evaluate('''() => ({pin:s.cats[0].sightings[0],map:renderExplore(),gpsFree:backupPayload(true)})''')
        assert saved['pin']['lat']==51.54 and saved['pin']['lng']==-.12
        assert 'Saved locations (1)' in saved['map']
        assert 'lat' not in saved['gpsFree']['cats'][0]['sightings'][0]
        assert not errors,errors
        await browser.close()
        print('PASS v3.7.2: Android status diagnostics, retry success, CatDex pin and GPS-free backup')

if __name__=='__main__':asyncio.run(main())
