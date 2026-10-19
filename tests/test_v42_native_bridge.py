"""v3.7.3: Android-only action bridge restores location/status/settings while leaving IndexedDB untouched."""
import asyncio, io, re, base64
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
    im=Image.new('RGB',(240,320),(139,113,94)); out=io.BytesIO()
    im.save(out,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()

async def main():
    raw=ROOT/'WhiskerHunt/Resources/Raw'
    html=(raw/'index_v42.html').read_text()
    assert 'window.whiskerNativeBridge=true;' in html
    assert 'window.whiskerAndroidShell=true;' not in html
    assert 'app_v42.js' in html and 'style_v42.css' in html
    assert 'window.whiskerNativeBridge' not in (ROOT/'BrowserPreview/index_v42.html').read_text()
    assert 'Source="index_v42.html"' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    project=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationDisplayVersion>3.7.3</ApplicationDisplayVersion>' in project
    assert '<ApplicationVersion>42</ApplicationVersion>' in project
    main=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
    assert 'case "app-settings":' in main
    assert 'Settings.ActionApplicationDetailsSettings' in main and '"package:" + context.PackageName' in main
    assert 'case "location":' in main and 'case "location-check":' in main
    js=(raw/'app_v42.js').read_text()
    assert js==(ROOT/'BrowserPreview/app.js').read_text()
    assert 'function hasAndroidActionBridge()' in js
    assert js.count('id="pin-check"')==1, 'checkbox ID must be unique'
    assert js.count('id="pin-status-check"')==1
    routes={
       "location.href='whiskerhunt://app-settings'":"window.__bridgeActions.push('settings')",
       "location.href='whiskerhunt://device-location-settings'":"window.__bridgeActions.push('device-location-settings')",
       "location.href='whiskerhunt://location?request='+encodeURIComponent(token)":"window.__bridgeActions.push('location:'+token)",
       "location.href='whiskerhunt://location-check?request='+encodeURIComponent(token)":"window.__bridgeActions.push('check:'+token)",
    }
    for original in routes:assert original in js,original
    for original, substitute in routes.items():js=js.replace(original,substitute)
    html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
    html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        await page.set_content(html)
        assert await page.evaluate('window.whiskerNativeBridge===true && !window.whiskerAndroidShell')
        await page.add_style_tag(content=(raw/'style_v42.css').read_text())
        await page.add_script_tag(content=js)
        im=photo()
        await page.evaluate('''im=>{
          window.__bridgeActions=[];window.__cats=new Map();window.__meta=new Map();
          const seed={id:'existing-cat',name:'Recovered cat',coat:'Tabby',personality:'Unknown',createdAt:new Date().toISOString(),photo:im,sightings:[{id:'seed1',at:new Date().toISOString()}]};
          window.__cats.set(seed.id,seed);
          window.openDb=async()=>({mock:true,transaction:()=>{const tx={objectStore:()=>({put:()=>{}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
          window.transact=async (store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return [...m.values()];if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value;}if(method==='delete'){m.delete(value)}};
          boot();
        }''',im)
        await page.wait_for_function('window.whiskerBootComplete === true')
        assert await page.evaluate('s.cats.length===1 && s.cats[0].name==="Recovered cat" && s.native===false')
        # Open an AR cat's name form. The bridge must operate even without whiskerNativeReady.
        await page.evaluate('''im=>{s.arModelKey=AR_CAT_MODELS[0].key;s.arHabitatKey=AR_HABITATS[0].key;s.encounterAr=true;s.encounterCaptured=true;s.image=im;s.encounterFocus={x:.5,y:.69};showVirtualNamingForm()}''',im)
        await page.locator('#virtual-pin').check()
        await page.locator('#virtual-pin-settings').click()
        await page.locator('#virtual-pin-device-location').click()
        actions=await page.evaluate('window.__bridgeActions')
        assert actions[:2]==['settings','device-location-settings'],actions
        await page.locator('#virtual-pin-status-check').click()
        await page.wait_for_function('window.__bridgeActions.some(x=>x.startsWith("check:"))')
        token=(await page.evaluate('window.__bridgeActions.filter(x=>x.startsWith("check:")).at(-1)')).split(':')[1]
        await page.evaluate('''token=>window.whiskerNativeLocationDiagnostic(token,{build:'3.7.3',coarse:true,fine:false,deviceEnabled:true})''',token)
        diagnostics=await page.locator('#virtual-pin-diagnostics').inner_text()
        assert 'Approximate: allowed' in diagnostics and 'Phone Location: on' in diagnostics, diagnostics
        assert 'Android app only' not in diagnostics
        await page.locator('#virtual-pin-allow').click()
        await page.wait_for_function('window.__bridgeActions.some(x=>x.startsWith("location:"))')
        token=(await page.evaluate('window.__bridgeActions.filter(x=>x.startsWith("location:")).at(-1)')).split(':')[1]
        await page.evaluate('''token=>window.whiskerNativeLocation(51.5341,-.0921,token)''',token)
        await page.wait_for_function('s.pendingApproxLocation!==null')
        await page.locator('#virtual-save-final').click()
        await page.wait_for_function('s.cats.length===2')
        after=await page.evaluate('''() => ({cats:s.cats.map(c=>c.name),sighting:s.cats.find(c=>c.virtual).sightings.at(-1),map:renderExplore(),safe:backupPayload(true)})''')
        assert 'Recovered cat' in after['cats']
        assert after['sighting']['lat']==51.53 and after['sighting']['lng']==-.09
        assert 'Saved locations (1)' in after['map']
        assert not any('lat' in s for c in after['safe']['cats'] for s in c['sightings'])
        # Real cat form has independent checkbox and status-check button IDs.
        await page.evaluate('im=>showCatForm(im)',im)
        assert await page.locator('#pin-check').count()==1
        assert await page.locator('#pin-status-check').count()==1
        await page.locator('#pin-check').check()
        assert await page.locator('#pin-status-check').is_visible()
        await page.locator('#pin-status-check').click()
        assert (await page.evaluate('window.__bridgeActions.filter(x=>x.startsWith("check:")).length'))==2
        assert await page.locator('#pin-check').is_checked(), 'checking diagnostics must not toggle opt-in'
        assert not errors,errors
        await browser.close()
        print('PASS v3.7.3: native action bridge, status/settings routing, saved pin, GPS-free backup, existing CatDex preserved')

if __name__=='__main__': asyncio.run(main())
