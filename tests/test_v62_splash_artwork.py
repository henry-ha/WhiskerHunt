from pathlib import Path
from hashlib import sha256
import json,re,asyncio,base64
from PIL import Image
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
N=ROOT/'WhiskerHunt'
RAW=N/'Resources/Raw'
WEB=ROOT/'BrowserPreview'
CS=(N/'WhiskerHunt.csproj').read_text()
assert '<ApplicationDisplayVersion>3.9.9</ApplicationDisplayVersion>' in CS
assert '<ApplicationVersion>62</ApplicationVersion>' in CS
assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in CS
assert 'hushhunt_approved_splash.png' in CS
assert (N/'Resources/Splash/hushhunt_approved_splash.png').exists()
assert not (N/'Resources/Splash/splash.svg').exists() # old art removed
with Image.open(N/'Resources/Splash/hushhunt_approved_splash.png') as img:
    assert img.size==(512,512)
assert 'Source="index_v62.html"' in (N/'MainPage.xaml').read_text()
for base in (RAW, WEB):
    html=(base/'index_v62.html').read_text()
    assert '3.9.9-62' in html and 'app_v62.js' in html and 'style_v62.css' in html
    js=(base/'app_v62.js').read_text()
    assert "const WHISKER_BUILD='3.9.9', WHISKER_BUILD_NUMBER=62" in js
    assert 'ART PACK 62' in js and 'field_art_v62/' in js
    assert 'field_art_v61/' not in js
    assert len(list((base/'field_art_v62').glob('*.webp')))==146
for f in (RAW/'field_art_v62').glob('*.webp'):
    assert sha256(f.read_bytes()).digest()==sha256((WEB/'field_art_v62'/f.name).read_bytes()).digest()
    with Image.open(f) as i:
        assert i.size in ((240,240),(180,180)),f
m=json.loads((RAW/'artwork_manifest_v62.json').read_text())
assert m['artPack']==62 and len(m['sha256'])==146
for f in (RAW/'field_art_v62').glob('*.webp'):
    assert m['sha256'][f.name]==sha256(f.read_bytes()).hexdigest()
for p in (N/'MainPage.xaml.cs',N/'Platforms/Android/HushArCoreActivity.cs'):
    code=p.read_text()
    assert 'field_art_v62' in code
    assert 'field_art_v61' not in code
assert 'whisker-hunt-state.json' in (N/'MainPage.xaml.cs').read_text()

async def browser_test():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        html=(WEB/'index_v62.html').read_text()
        html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
        html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
        await page.set_content(html)
        await page.add_style_tag(content=(WEB/'style_v62.css').read_text())
        await page.add_script_tag(content=(WEB/'app_v62.js').read_text())
        await page.evaluate('boot()')
        await page.wait_for_function('window.whiskerBootComplete === true')
        await page.evaluate('''() => {s.spottedSpecies='Snail'; const root = document.createElement('div');root.id='field-guide-types';document.body.appendChild(root);renderFieldGuideVarieties();}''')
        assert await page.get_by_text('ART PACK 62').count()==0  # heading only appears with full form
        img=page.locator('#field-guide-types img').first
        assert 'field_art_v62/' in await img.get_attribute('src')
        src=await img.get_attribute('src')
        file=WEB/src
        data='data:image/webp;base64,'+base64.b64encode(file.read_bytes()).decode('ascii')
        await img.evaluate('(el,value)=>el.src=value',data)
        await page.wait_for_function('document.querySelector("#field-guide-types img")?.naturalWidth > 0')
        await page.screenshot(path='/mnt/data/HushHunt_v3.9.9_ArtPack_Smoke.png',full_page=False)
        assert not errors,errors
        await browser.close()
asyncio.run(browser_test())
print('PASS v3.9.9: approved splash used; current v62 pack 146 pictures; Android/browser assets match; real browser img loads; storage compatibility')
