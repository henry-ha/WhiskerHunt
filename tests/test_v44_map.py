"""v3.8.0 map regression: visible private marker, explicit consent, Android external-browser intent."""
import asyncio, base64, io, re
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def fake_photo():
    im=Image.new('RGB',(100,120),(130,155,185));b=io.BytesIO();im.save(b,format='JPEG');return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()

async def main():
    raw=ROOT/'WhiskerHunt'/'Resources'/'Raw'
    assert (ROOT/'WhiskerHunt/MainPage.xaml').read_text().find('Source="index_v44.html"')>=0
    csproj=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationDisplayVersion>3.8.0</ApplicationDisplayVersion>' in csproj and '<ApplicationVersion>44</ApplicationVersion>' in csproj
    native=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
    assert 'Android.Content.Intent.ActionView' in native and 'context.StartActivity(intent);' in native
    assert 'target.Host.Equals("www.openstreetmap.org"' in native
    assert 'window.whiskerExternalMapResult' in native
    assert (raw/'app_v44.js').read_bytes()==(ROOT/'BrowserPreview/app.js').read_bytes()
    assert (raw/'style_v44.css').read_bytes()==(ROOT/'BrowserPreview/style.css').read_bytes()
    assert 'window.whiskerNativeBridge=true;' in (raw/'index_v44.html').read_text()
    js=(ROOT/'BrowserPreview/app.js').read_text()
    assert 'function askOpenStreetMap(' in js
    # Simulate native action bridge without asking Chromium to navigate to an unhandled scheme.
    js=js.replace("location.href='whiskerhunt://open?url='+encodeURIComponent(url);","window.__externalRoutes.push(url);")
    html=(ROOT/'BrowserPreview/index.html').read_text()
    html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
    html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=js)
        image=fake_photo()
        await page.evaluate('''img=>{
          window.__externalRoutes=[]; window.__cats=new Map();window.__meta=new Map();
          window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{const tx={objectStore:()=>({put:()=>{}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
          window.transact=async(store,mode,method,value)=>{
            const m=store==='cats'?window.__cats:window.__meta;
            if(method==='getAll')return [...m.values()];
            if(method==='get')return m.get(value);
            if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value;}
          };
          const existing={id:'cat-one',name:'Socks',coat:'Tabby',personality:'Friendly',photo:img,createdAt:new Date().toISOString(),sightings:[{id:'sighting-one',at:new Date().toISOString(),lat:51.53,lng:-0.11}]};
          window.__cats.set(existing.id,existing);boot();
        }''',image)
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.locator('[data-nav="explore"]').click()
        await page.locator('.map-pin-v43').wait_for()
        assert await page.locator('.map-pin-v43').count()==1
        assert await page.locator('.map-pin-label').inner_text()=='Socks'
        assert 'Socks' in await page.locator('#map-selected-card').inner_text()
        assert 'Saved locations (1)' in await page.locator('#view').inner_text()
        pos=await page.locator('.map-pin-v43').evaluate('(el)=>({left:el.style.left,top:el.style.top,size:getComputedStyle(el).width})')
        assert pos['left']=='50%' and pos['top']=='50%' and pos['size']=='56px',pos
        assert await page.locator('.map-pin-label').evaluate('(el)=>getComputedStyle(el).rotate')=='none'
        # Pin layout must remain in bounds and separate duplicate approximate areas.
        xs=await page.evaluate('''()=>{const g=[{lat:51.53,lng:-.11},{lat:51.53,lng:-.11},{lat:51.54,lng:-.12}];return g.map((v,i)=>privatePlotPosition(v,g,i))}''')
        assert xs[0] != xs[1] and all(13 <= p['x'] <= 87 and 22 <= p['y'] <= 78 for p in xs)
        await page.screenshot(path=str(ROOT/'WhiskerHunt_v3.8.0_MapPreview.png'),full_page=True)
        # The user can select a marker in-place, and no third-party navigation occurs.
        await page.locator('[data-map-select="0"]').first.click()
        assert await page.evaluate('window.__externalRoutes.length')==0
        before=await page.evaluate('JSON.stringify({cats:backupPayload().cats,profile:backupPayload().profile})')
        # An explicit consent dialog is shown before the browser launch.
        await page.locator('.map-street-btn').click()
        assert await page.get_by_role('heading',name='Open a street map?').is_visible()
        assert await page.evaluate('window.__externalRoutes.length')==0
        await page.locator('#map-stay-private').click()
        assert await page.evaluate('window.__externalRoutes.length')==0
        await page.locator('.map-street-btn').click()
        await page.evaluate('window.whiskerNativeBridge=true')
        await page.locator('#map-open-browser').click()
        external=await page.evaluate('window.__externalRoutes')
        assert len(external)==1 and external[0].startswith('https://www.openstreetmap.org/'),external
        assert 'mlat=51.53' in external[0] and 'mlon=-0.11' in external[0]
        after=await page.evaluate('JSON.stringify({cats:backupPayload().cats,profile:backupPayload().profile})')
        assert before==after,'Opening the map must never mutate CatDex data'
        await page.evaluate('window.whiskerExternalMapResult(false)')
        assert 'No browser could open' in await page.locator('#toast').inner_text()
        assert not errors,errors
        print('PASS v3.8.0: private marker/name/card, explicit OSM consent, native browser route, data unchanged')
        await browser.close()
if __name__=='__main__':asyncio.run(main())
