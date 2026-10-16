"""Smoke test for Whisker Hunt browser mode. python -m pip install playwright; playwright install chromium."""
import asyncio
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parent.parent

def photo(rgb):
    image=Image.new('RGB',(500,380),rgb)
    d=ImageDraw.Draw(image)
    d.ellipse((120,30,370,300),fill=(180,160,130))
    d.ellipse((160,180,180,204),fill='black')
    d.ellipse((300,180,320,204),fill='black')
    data=io.BytesIO()
    image.save(data,format='JPEG',quality=90)
    return data.getvalue()

async def test():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        context=await browser.new_context(viewport={'width':390,'height':844},accept_downloads=True)
        page=await context.new_page()
        errors=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        html=(ROOT/'BrowserPreview'/'index.html').read_text().replace('<script src="app.js" defer></script>', '').replace('<link rel="stylesheet" href="style.css">', '')
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview'/'style.css').read_text())
        await page.add_script_tag(content=(ROOT/'BrowserPreview'/'app.js').read_text())
        await page.evaluate('''() => {
          window.__cats=new Map();window.__meta=new Map();
          window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{
            const tx={objectStore:(store)=>({put:(value)=>{
              const m=store==='cats'?window.__cats:window.__meta;
              m.set(store==='cats'?value.id:value.key,value);
            }})};setTimeout(()=>tx.oncomplete?.(),0);return tx;
          }});
          window.transact=async (store,mode,method,value)=>{
            const m=store==='cats'?window.__cats:window.__meta;
            if(method==='getAll')return Array.from(m.values());
            if(method==='get')return m.get(value);
            if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}
            if(method==='delete'){m.delete(value);return}
          };
          boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete === true')

        async def finish_encounter(use_lure=False):
            await page.locator('#encounter-stage').wait_for()
            if use_lure:
                await page.locator('#tool-lure').click()
                await page.evaluate('handleEncounterHit("lure")')
            await page.evaluate('handleEncounterHit("ball")')
            await page.locator('#encounter-continue').wait_for()
            await page.locator('#encounter-continue').click()

        assert await page.locator('.hero-title').is_visible()
        await page.locator('#hero-catch').click()
        await page.locator('#library-input').set_input_files({'name':'a.jpg','mimeType':'image/jpeg','buffer':photo((115,180,215))})
        await finish_encounter(use_lure=True)
        await page.locator('#cat-name').fill('Pixel')
        await page.locator('#cat-coat').select_option('Tabby')
        await page.locator('#cat-personality').select_option('Curious')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.get_by_text('Pixel',exact=True).first.wait_for()
        assert (await page.locator('.cat-tile').count()) == 1
        await page.locator('.cat-tile').first.click()
        assert await page.get_by_text('Friendship',exact=False).count() >= 1
        await page.locator('#edit-cat').click()
        await page.locator('#edit-name').fill('Pixel Junior')
        await page.locator('#edit-note').fill('Calm and fluffy.')
        await page.locator('#edit-personality').select_option('Playful')
        await page.locator('#edit-save').click()
        assert await page.get_by_text('Pixel Junior',exact=True).count() >= 1
        assert await page.get_by_text('Playful',exact=False).count() >= 1
        await page.locator('#fav-cat').click()
        await page.locator('[data-close]').first.click()
        assert await page.locator('.bingo-tile').count()==8
        assert await page.locator('.bingo-tile.found').count()==1
        await page.get_by_role('button',name='Favourites').click()
        assert await page.locator('.cat-tile').count()==1
        await page.locator('.cat-tile').click()
        await page.locator('#save-card').click()
        await page.wait_for_function('window.whiskerCardBase64().length > 1000')
        # Return sighting for same cat from different image
        await page.locator('[data-close]').first.click()
        await page.locator('#nav-catch').click()
        await page.locator('#library-input').set_input_files({'name':'b.jpg','mimeType':'image/jpeg','buffer':photo((115,205,140))})
        await finish_encounter()
        await page.locator('#mode-repeat').click()
        await page.locator('#repeat-cat').select_option(index=0)
        await page.locator('#repeat-note').fill('Seen walking again.')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.locator('.cat-tile').click()
        assert await page.get_by_text('2 sightings',exact=False).count() >= 1
        assert await page.locator('[data-edit-sighting]').count() == 2
        await page.locator('[data-edit-sighting]').first.click()
        await page.locator('#sighting-note').fill('Returned on Tuesday')
        await page.locator('#save-sighting').click()
        assert await page.get_by_text('Returned on Tuesday').count()>=1
        await page.locator('[data-edit-sighting]').first.click()
        page.once('dialog',lambda dlg: asyncio.create_task(dlg.accept()))
        await page.locator('#delete-sighting').click()
        await page.wait_for_timeout(250)
        # Browser restore round trip
        payload=await page.evaluate('window.whiskerBackupBase64()')
        assert json.loads(__import__('base64').b64decode(payload)).get('cats')
        await page.evaluate('''() => {s.cats=[];s.profile={name:'New explorer',xp:0,claimed:[]};window.confirm=()=>true;}''')
        await page.evaluate('''(backup) => loadBackupText(JSON.stringify(backup))''',json.loads(__import__('base64').b64decode(payload)))
        assert await page.evaluate('s.cats.length') == 1
        assert await page.evaluate('s.cats[0].name') == 'Pixel Junior'
        assert await page.evaluate('s.profile.xp') >= 100
        # Critical native restore regression: no IndexedDB transaction should be attempted.
        await page.evaluate('''() => {s.native=true;s.db={native:true};s.cats=[];window.whiskerNativeReady=true;nativeSync=async()=>{};}''')
        await page.evaluate('''(backup) => loadBackupText(JSON.stringify(backup))''',json.loads(__import__('base64').b64decode(payload)))
        assert await page.evaluate('s.cats.length') == 1
        assert await page.evaluate('s.cats[0].name') == 'Pixel Junior'
        assert await page.evaluate('s.cats[0].personality') == 'Playful'
        await page.locator('[data-close]').first.click()
        await page.locator('#nav-catch').click()
        await page.locator('#library-input').set_input_files({'name':'duplicate.jpg','mimeType':'image/jpeg','buffer':photo((115,180,215))})
        await finish_encounter()
        await page.locator('#cat-name').fill('Duplicate')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        assert await page.get_by_text('This photo is already collected.',exact=False).is_visible()
        assert await page.evaluate('s.cats.length')==1
        await page.locator('[data-close]').first.click()
        assert await page.get_by_text('Pixel Junior',exact=True).count() >= 1
        await page.locator('[data-nav="quests"]').click()
        assert await page.get_by_role('heading',name='Weekly adventures',exact=True).count()==1
        assert await page.get_by_text('Familiar faces').count()==1
        assert await page.get_by_text('Adventure days').count()==1
        assert not errors,errors
        # v0.4: the new private timeline is searchable and opens the right cat.
        await page.locator('#head-profile').click()
        await page.locator('[data-go="journal"]').click()
        assert await page.get_by_role('heading',name='Sighting journal').count()==1
        assert await page.locator('.journal-card').count()==1
        await page.locator('#journal-search').fill('not-a-real-cat-name')
        assert await page.locator('.journal-card').count()==0
        await page.locator('#journal-search').fill('Pixel')
        assert await page.locator('.journal-card').count()==1
        await page.locator('[data-journal-filter="Reunions"]').click()
        assert await page.locator('.journal-card').count()==0
        await page.locator('[data-journal-filter="New cats"]').click()
        assert await page.locator('.journal-card').count()==1
        await page.screenshot(path=str(ROOT/'tests'/'journal-preview.png'),full_page=True)
        await page.locator('.journal-card').click()
        assert await page.locator('#more-sighting').count()==1
        # Spot again from the CatDex must select that cat automatically.
        cat_id=await page.evaluate('s.cats[0].id')
        await page.locator('#more-sighting').click()
        await page.locator('#library-input').set_input_files({'name':'reunion.jpg','mimeType':'image/jpeg','buffer':photo((155,155,215))})
        await finish_encounter()
        assert await page.locator('#mode-repeat').evaluate('(el)=>el.classList.contains("selected")')
        assert await page.locator('#repeat-cat').input_value()==cat_id
        await page.locator('[data-close]').first.click()
        # merge backups cannot silently lower the user's XP or remove other cats.
        before_xp=await page.evaluate('s.profile.xp')
        backup=json.loads(__import__('base64').b64decode(payload))
        backup['profile']['xp']=0
        backup['profile']['claimed']=[]
        await page.evaluate('(b)=>loadBackupText(JSON.stringify(b))',backup)
        assert await page.evaluate('s.profile.xp')==before_xp
        assert await page.evaluate('s.cats.length')==1
        # Reject untrusted IDs in JSON backups, which also protects HTML data attributes.
        backup['cats'][0]['id']='bad" onmouseover="alert(1)'
        await page.evaluate('(b)=>loadBackupText(JSON.stringify(b))',backup)
        assert await page.evaluate('s.cats.length')==1
        assert await page.evaluate('s.cats[0].id')==cat_id
        assert not errors,errors
        screenshot=ROOT/'tests'/'smoke-test.png'
        await page.screenshot(path=str(screenshot),full_page=True)
        print('PASSED v1.2 browser smoke tests (encounter flow, collection, journal, reunion, safe merge, ID validation). Screenshot:',screenshot)
        await browser.close()

if __name__=='__main__':
    asyncio.run(test())
