"""Hush Hunt v3.10.3 educational guide release smoke + capture compatibility."""
from pathlib import Path
from PIL import Image
import asyncio,json,re
from playwright.async_api import async_playwright
r=Path(__file__).resolve().parents[1]
w=r/'BrowserPreview';a=r/'WhiskerHunt/Resources/Raw'

def static_checks():
    facts=json.loads((w/'field_guide_facts_v66.json').read_text())
    assert len(facts['groups'])==17
    assert sum(map(len,facts['types'].values()))==128
    for key in ['app_v66.js','style_v66.css','field_guide_facts_v66.json','sw.js']:
        assert (w/key).read_bytes()==(a/key).read_bytes(),key
    assert '<ApplicationVersion>66</ApplicationVersion>' in (r/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationDisplayVersion>3.10.3</ApplicationDisplayVersion>' in (r/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert 'uk.whiskerhunt.mobile' in (r/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert 'index_v66.html' in (r/'WhiskerHunt/MainPage.xaml').read_text()
    for f in (w/'field_art_v66').glob('*.webp'):
        assert f.read_bytes()==(a/'field_art_v66'/f.name).read_bytes(),f.name
        with Image.open(f) as im:im.verify()
    assert len(list((w/'field_art_v66').glob('*.webp')))==146
    for key in ['other-group','other-other-animal','other-not-sure']:
        assert (w/'field_art_v66'/f'{key}.webp').read_bytes()!=(w/'field_art_v65'/f'{key}.webp').read_bytes()

async def browser_checks():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
        body=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',(w/'index.html').read_text())
        body=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',body)
        await page.set_content(body)
        await page.add_style_tag(content=(w/'style_v66.css').read_text())
        await page.add_script_tag(content=(w/'app_v66.js').read_text())
        await page.evaluate('''()=>{const store={cats:new Map(),meta:new Map()};window.transact=async(kind,mode,method,val)=>{const m=store[kind];if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(val);if(method==='put'){m.set(val.id||val.key,val);return val}};window.openDb=async()=>({});boot();}''')
        await page.wait_for_function('window.whiskerBootComplete === true')
        assert await page.locator('#hush-guide-from-home').count()==1
        assert await page.locator('#hush-direct-live').count()==1
        assert await page.locator('#hush-direct-ar').count()==1
        await page.locator('#hush-guide-from-home').click()
        assert await page.locator('#hush-fullscreen-guide').is_visible()
        assert await page.locator('[data-hush-guide-group]').count()==17
        await page.locator('[data-hush-guide-group="Bird"]').click()
        assert await page.locator('[data-hush-guide-type]').count()==14
        await page.locator('[data-hush-guide-type="Robin"]').click()
        assert 'Orange-red face' in await page.locator('.hush-guide-feature').inner_text()
        assert await page.locator('.hush-guide-feature img').get_attribute('src')=='field_art_v66/bird-robin.webp'
        await page.screenshot(path=str(r/'HushHunt_v3.10.3_Guide_Preview.png'))
        await page.keyboard.press('Escape')
        assert await page.locator('#hush-fullscreen-guide').count()==0
        await page.locator('[data-nav="dex"]').click()
        await page.locator('#hush-guide-from-dex').click()
        assert await page.locator('#hush-fullscreen-guide').count()==1
        await page.locator('#hush-guide-close').click()
        assert await page.locator('#hush-fullscreen-guide').count()==0
        # Inject a mock real-world form UI, then exercise classification handoff.
        await page.evaluate('''()=>{
          s.spottedSpecies='Cat';s.spottedDetail='';
          const wrap=document.createElement('div');wrap.id='test-guide-form';
          wrap.innerHTML='<select id="wildlife-species"><option>Cat</option><option>Bird</option></select><select id="cat-coat"><option>Other</option><option>Tabby</option></select><input id="wildlife-detail"><div id="field-guide-types"></div>';
          document.body.appendChild(wrap);
          wrap.querySelector('#wildlife-species').addEventListener('change',()=>{s.spottedSpecies=wrap.querySelector('#wildlife-species').value;s.spottedDetail=''});
          renderFieldGuideVarieties();
        }''')
        assert await page.locator('#hush-guide-from-form').count()==1
        await page.locator('#hush-guide-from-form').click()
        await page.locator('[data-hush-guide-group="Bird"]').click()
        await page.locator('[data-hush-guide-type="Robin"]').click()
        await page.locator('#hush-guide-use').click()
        assert await page.locator('#wildlife-species').input_value()=='Bird'
        assert await page.locator('#wildlife-detail').input_value()=='Robin'
        assert await page.locator('#hush-fullscreen-guide').count()==0
        await page.locator('#test-guide-form').evaluate('(n)=>n.remove()')
        assert await page.evaluate('s.cats.length')==0
        assert not errors,errors
        await browser.close()
if __name__=='__main__':
 static_checks();asyncio.run(browser_checks());print('PASS v66: 17 groups, 128 clues, 146 local art files, modal navigation, selection handoff, storage unchanged')
