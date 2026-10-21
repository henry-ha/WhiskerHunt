"""Hush Hunt 3.8.3: offline image cards for all species, persisted field types, safe upgrades."""
import asyncio, base64, io, json
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def img(rgb):
    from PIL import ImageDraw
    im=Image.new('RGB',(320,400),rgb);d=ImageDraw.Draw(im);d.ellipse((23,45,230,238),fill=(255-rgb[0],255-rgb[1],255-rgb[2]));d.rectangle((rgb[0],295,rgb[0]+90,355),fill=(rgb[2],rgb[0],rgb[1]));buf=io.BytesIO();im.save(buf,format='JPEG',quality=82)
    return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()

async def main():
    assert '<ApplicationTitle>Hush Hunt</ApplicationTitle>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    assert '<ApplicationVersion>47</ApplicationVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    a=ROOT/'BrowserPreview';b=ROOT/'WhiskerHunt/Resources/Raw'
    assert (a/'app_v47.js').read_bytes()==(b/'app_v47.js').read_bytes()
    assert (a/'style_v47.css').read_bytes()==(b/'style_v47.css').read_bytes()
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
        errors=[];badimgs=[];page.on('pageerror',lambda err:errors.append(str(err)))
        html=(a/'index.html').read_text()
        import re
        html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
        html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
        await page.set_content(html)
        await page.add_style_tag(content=(a/'style_v47.css').read_text())
        await page.add_script_tag(content=(a/'app_v47.js').read_text())
        # Browser scripts are self-contained. Map 141 local picture files to data URIs
        # for this test's non-network about:blank page.
        art={p.name:base64.b64encode(p.read_bytes()).decode() for p in (a/'field_art').glob('*.webp')}
        await page.evaluate('''pictures=>{window.fieldGuideArt=(group,type)=>{const x=v=>String(v).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');return 'data:image/webp;base64,'+pictures[x(group)+'-'+(type?x(type):'group')+'.webp']}}''',art)
        await page.evaluate('''async()=>{window.__cats=new Map();window.__meta=new Map();window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{const tx={objectStore:store=>({put:value=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value);}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return [...m.values()];if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value;}if(method==='delete')m.delete(value)};await boot()}''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        assert 'Hush' in await page.locator('.brand').inner_text()
        assert await page.evaluate('Object.keys(FIELD_GUIDE_VARIETIES).length')==17
        assert await page.evaluate('Object.values(FIELD_GUIDE_VARIETIES).every(types=>types.length>=4)')
        assert await page.evaluate('Object.values(FIELD_GUIDE_VARIETIES).reduce((t,a)=>t+a.length,0)')==128
        # Legacy cat still loads, with unchanged original coat and collection keys.
        await page.evaluate('''image=>{s.cats=[{id:'legacy',name:'Mochi',coat:'Tabby',createdAt:new Date().toISOString(),photo:image,sightings:[{id:'oldvisit',at:new Date().toISOString()}]}];render();}''',img((150,100,70)))
        async def show_animal(photodata):
            await page.evaluate('''image=>{const video=document.createElement('video');liveCamera={active:true,stream:{getTracks:()=>[]},video,frames:[{image,quality:null,at:Date.now()}],timer:null,sampling:false,dragging:false};s.encounterAr=false;s.realLiveProof={ready:true,images:new Set([image])};s.image=image;showCatForm(image)}''',photodata)
        await show_animal(img((80,145,77)))
        assert await page.locator('#field-guide-species .field-guide-tile').count()==17
        assert await page.locator('#field-guide-types .field-guide-tile').count()==12
        assert await page.locator('#field-guide-species').is_visible()
        # Actual offline photos/illustrations resolve; no internet image fetches.
        await page.locator('[data-guide-group="Snail"]').click()
        assert await page.locator('#wildlife-species').input_value()=='Snail'
        assert await page.locator('[data-guide-type="Garden Snail"]').count()==1
        await page.wait_for_function("document.querySelector('[data-guide-type=\"Garden Snail\"] img').naturalWidth>0")
        assert await page.locator('#field-guide-species').is_hidden()
        await page.locator('[data-guide-type="Garden Snail"]').click()
        assert await page.locator('#wildlife-detail').input_value()=='Garden Snail'
        await page.locator('#cat-name').fill('Shelly')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.wait_for_function("s.cats.some(c=>c.name==='Shelly')")
        snail=await page.evaluate("s.cats.find(c=>c.name==='Shelly')")
        assert snail['species']=='Snail' and snail['speciesDetail']=='Garden Snail',snail
        assert not snail.get('virtual')
        assert await page.evaluate('s.cats.find(c=>c.id==="legacy").coat')=='Tabby'
        # Cat coat cards still write the original coat field, preserving Bingo.
        await show_animal(img((90,120,170)))
        if await page.locator('#field-guide-species').is_hidden():await page.locator('#change-species').click()
        await page.locator('[data-guide-group="Cat"]').click()
        await page.locator('[data-guide-type="Tuxedo"]').click()
        assert await page.locator('#cat-coat').input_value()=='Tuxedo'
        assert await page.locator('#cat-name').count()==1
        await page.locator('#real-cat').check()
        await page.locator('#cat-name').fill('Mittens')
        await page.locator('#save-catch').click()
        await page.wait_for_function("s.cats.some(c=>c.name==='Mittens')",timeout=6000)
        assert await page.evaluate('s.cats.find(c=>c.name==="Mittens").coat')=='Tuxedo'
        # Every animal group renders its 4+ visual choices, plus fallback and custom label.
        for group in await page.evaluate('SPECIES'):
            await show_animal(img((100,88,99)))
            await page.locator('#change-species').click() if await page.locator('#field-guide-species').is_hidden() else None
            await page.locator(f'[data-guide-group="{group}"]').click()
            assert await page.locator('#field-guide-types .field-guide-tile').count()>=4,group
            n=await page.locator('#field-guide-types .field-guide-tile img').count();assert n>=4
            await page.wait_for_function("[...document.querySelectorAll('#field-guide-types .field-guide-tile img')].every(i=>i.complete&&i.naturalWidth>0)")
            assert await page.locator('#field-guide-custom').count()==1
            await page.evaluate('closeModal()')
        # A saved non-cat can be retyped without losing photo, location, history.
        await page.evaluate("editCat(s.cats.find(c=>c.name==='Shelly'))")
        assert await page.locator('[data-guide-type="Garden Snail"]').count()==1
        await page.locator('[data-guide-type="Grove Snail"]').click()
        assert await page.locator('#edit-species-detail').input_value()=='Grove Snail'
        await page.locator('#edit-save').click()
        await page.wait_for_function("s.cats.some(c=>c.name==='Shelly'&&c.speciesDetail==='Grove Snail')")
        assert await page.evaluate('s.cats.find(c=>c.name==="Shelly").sightings.length')==1
        result=await page.evaluate('backupPayload()')
        assert result['version']==1
        assert result['cats'][0]['name']=='Mochi'
        assert any(c.get('speciesDetail')=='Grove Snail' for c in result['cats'])
        assert not errors,errors
        await page.evaluate('navigate("dex")')
        await page.locator('[data-filter="Species:Snail"]').click()
        assert await page.locator('.variant-album-tile').count()==7
        assert await page.locator('.variant-album-tile.unlocked').count()==1
        assert 'Grove Snail' in await page.locator('.variant-album').inner_text()
        await page.locator('.variant-album').scroll_into_view_if_needed()
        await page.evaluate("document.getElementById('toast').classList.add('hidden')")
        await page.screenshot(path=str(ROOT/'HushHunt_v3.8.3_Variety_Album_Preview.png'))
        await page.evaluate('navigate("home")')
        await page.screenshot(path=str(ROOT/'HushHunt_v3.8.3_Home_Preview.png'))
        await show_animal(img((80,142,73)))
        await page.locator('[data-guide-group="Snail"]').click()
        await page.locator('#field-guide-types').scroll_into_view_if_needed()
        await page.evaluate("document.getElementById('toast').classList.add('hidden')")
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(ROOT/'HushHunt_v3.8.3_FieldGuide_Preview.png'),full_page=False)
        print('PASS: Hush Hunt branding, 17 groups, 128 types, offline images, snail/cat save, all type pictures, edit, v1 backup, legacy photos')
        await browser.close()
if __name__=='__main__':asyncio.run(main())
