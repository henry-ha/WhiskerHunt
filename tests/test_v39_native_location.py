"""v3.7 regression: Android coarse permission fallback + virtual cat location flows."""
import asyncio, base64, io, re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
    image=Image.new('RGB',(240,320),(110,110,125));out=io.BytesIO()
    image.save(out,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
    cs=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    native=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
    provider=(ROOT/'WhiskerHunt/Platforms/Android/AndroidApproximateLocationProvider.cs').read_text()
    assert '<ApplicationVersion>39</ApplicationVersion>' in cs
    assert '<ApplicationDisplayVersion>3.7.0</ApplicationDisplayVersion>' in cs
    assert 'Source="index_v39.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    assert 'AndroidApproximateLocationProvider.HasForegroundPermission()' in native
    assert 'permitted = AndroidApproximateLocationProvider.HasForegroundPermission();' in native
    assert 'AndroidApproximateLocationProvider.TryGetAsync(TimeSpan.FromSeconds(12))' in native
    assert 'await FailAsync(AndroidApproximateLocationProvider.HasForegroundPermission() ? "no_fix" : "permission")' in native
    assert 'RequestSingleUpdate' in provider and 'AccessCoarseLocation' in provider
    assert 'manager.RemoveUpdates(listener)' in provider
    src=(ROOT/'BrowserPreview/app.js').read_text()
    route="location.href='whiskerhunt://location?request='+encodeURIComponent(token)"
    assert route in src
    assert "Save cat without a pin" in src
    for directory in [ROOT/'BrowserPreview',ROOT/'WhiskerHunt/Resources/Raw']:
        assert (directory/'app_v39.js').read_text()==src
        assert 'app_v39.js' in (directory/'index_v39.html').read_text()
    script=src.replace(route,'window.__nativeGpsRequests.push(token)')
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text()
        html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
        html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=script)
        await page.evaluate('''() => {
          window.__cats=new Map();window.__meta=new Map();window.__nativeGpsRequests=[];
          window.openDb=async()=>({mock:true,transaction:()=>{const tx={objectStore:(store)=>({put:(value)=>{(store==='cats'?window.__cats:window.__meta).set(store==='cats'?value.id:value.key,value)}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
          window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete'){m.delete(value);return}};
          boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.evaluate('window.whiskerAndroidShell=true;window.whiskerNativeReady=true')
        await page.evaluate('''im=>{s.arModelKey=AR_CAT_MODELS[0].key;s.arHabitatKey=AR_HABITATS[0].key;s.encounterAr=true;s.encounterCaptured=true;s.image=im;s.encounterFocus={x:.5,y:.69};showVirtualNamingForm()}''',photo())
        await page.locator('#virtual-pin').check()
        await page.locator('#virtual-pin-allow').click()
        await page.wait_for_function('window.__nativeGpsRequests.length===1')
        first=await page.evaluate('window.__nativeGpsRequests[0]')
        await page.evaluate('token=>window.whiskerNativeLocationError(token,"permission")',first)
        assert await page.locator('#virtual-pin-failure').is_visible()
        assert await page.locator('#virtual-pin-skip').is_visible()
        # Child-friendly explicit escape hatch: persist photos, but never secretly save GPS.
        await page.locator('#virtual-pin-skip').click()
        await page.wait_for_function('s.cats.length===1')
        assert await page.evaluate('s.cats[0].sightings[0].lat===null')
        assert await page.evaluate('s.profile.xp===0')
        # Next encounter: native Android provider supplies a valid approximate location.
        await page.evaluate('''im=>{s.arModelKey=AR_CAT_MODELS[1].key;s.arHabitatKey=AR_HABITATS[1].key;s.encounterAr=true;s.encounterCaptured=true;s.image=im;s.encounterFocus={x:.5,y:.69};showVirtualNamingForm()}''',photo())
        await page.locator('#virtual-pin').check()
        await page.locator('#virtual-pin-allow').click()
        await page.wait_for_function('window.__nativeGpsRequests.length===2')
        second=await page.evaluate('window.__nativeGpsRequests[1]')
        await page.evaluate('token=>window.whiskerNativeLocation(51.53739,-.1345,token)',second)
        await page.wait_for_function('s.pendingApproxLocation!==null')
        await page.locator('#virtual-save-final').click()
        await page.wait_for_function('s.cats.length===2')
        saved=await page.evaluate('''() => ({pin:s.cats[1].sightings[0],map:renderExplore(),safe:backupPayload(true)})''')
        assert saved['pin']['lat']==51.54 and saved['pin']['lng']==-.13
        assert 'Saved locations (1)' in saved['map']
        assert 'lat' not in saved['safe']['cats'][1]['sightings'][0]
        assert not errors,errors
        print('PASS v3.7 Android bridge simulation: failed GPS still lets child save cat; second catch saves private rounded map pin')
        await browser.close()

if __name__=='__main__': asyncio.run(main())
