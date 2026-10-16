"""v1.5: actionable photo checks, safe replacement, and stale-selection protection."""
import asyncio, base64, io
from pathlib import Path
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def picture(mode='dark'):
    im=Image.new('RGB',(600,400),(8,8,8) if mode=='dark' else (120,120,120))
    if mode=='detail':
        d=ImageDraw.Draw(im)
        for y in range(0,400,12):
            for x in range(0,600,12):
                d.rectangle((x,y,x+11,y+11),fill=(232,235,238) if (x//12+y//12)%2 else (24,28,35))
    b=io.BytesIO();im.save(b,format='JPEG',quality=90)
    return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844},has_touch=True)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
        await page.evaluate('''() => {window.__cats=new Map();window.__meta=new Map();
            window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{const tx={objectStore:(store)=>({put:(value)=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value);}})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
            window.transact=async (store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}if(method==='delete'){m.delete(value);return}};boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        dark=picture('dark');detail=picture('detail')
        low=await page.evaluate('im=>assessPhotoQuality(im)',dark)
        good=await page.evaluate('im=>assessPhotoQuality(im)',detail)
        assert low['label']=='Too dark',low
        assert good['label'] not in ('Too dark','Low detail'),good
        assert good['detail']>low['detail'],(low,good)
        await page.evaluate('(im)=>beginEncounter(im)',dark)
        await page.locator('#encounter-stage').wait_for()
        assert await page.get_by_text('Too dark',exact=False).count()>=1
        # A tap on the status overlay is not a photo tap.
        before=await page.evaluate('s.encounterFocus')
        await page.locator('#encounter-status').click()
        assert await page.evaluate('s.encounterFocus')==before
        # The picker may be cancelled: do not destroy the current photo/encounter.
        await page.evaluate('''() => {window.__retakes=0;window.__replaces=0;
          document.getElementById('image-input').click=()=>window.__retakes++;
          document.getElementById('library-input').click=()=>window.__replaces++;}''')
        await page.locator('#encounter-retake').click()
        await page.locator('#encounter-replace').click()
        assert await page.evaluate('[window.__retakes,window.__replaces]')==[1,1]
        assert await page.evaluate('s.image')==dark
        assert await page.locator('#encounter-stage').is_visible()
        # Select a new photo via the same browser file input used by the app.
        raw=base64.b64decode(detail.split(',',1)[1])
        await page.locator('#library-input').set_input_files({'name':'better.jpg','mimeType':'image/jpeg','buffer':raw})
        await page.wait_for_function('(old)=>s.image!==old',arg=dark)
        await page.locator('#encounter-stage').wait_for()
        assert await page.get_by_text('Too dark',exact=False).count()==0
        assert not await page.evaluate('s.encounterCaptured')
        assert not await page.evaluate('s.encounterLured')
        assert await page.evaluate('s.cats.length')==0
        await page.screenshot(path=str(ROOT/'tests/v15-photo-retake.png'),full_page=True)
        # Replacing a photo must not alter CatDex/XP until the user saves.
        await page.evaluate('handleEncounterHit("ball")')
        await page.locator('#encounter-continue').wait_for()
        await page.locator('#encounter-continue').click()
        await page.locator('#cat-name').fill('Nova')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.get_by_text('Nova',exact=True).first.wait_for()
        assert await page.evaluate('s.cats.length')==1
        xp=await page.evaluate('s.profile.xp')
        cat_id=await page.evaluate('s.cats[0].id')
        await page.evaluate('(id)=>startCatch(id)',cat_id)
        await page.evaluate('(im)=>beginEncounter(im)',dark)
        await page.locator('#encounter-stage').wait_for()
        await page.locator('#encounter-replace').click()
        assert await page.evaluate('s.cats.length')==1
        assert await page.evaluate('s.profile.xp')==xp
        await page.evaluate('handleEncounterHit("ball")')
        await page.locator('#encounter-continue').wait_for()
        await page.locator('#encounter-continue').click()
        assert await page.locator('#mode-repeat').evaluate('(el)=>el.classList.contains("selected")')
        assert await page.locator('#repeat-cat').input_value()==cat_id
        await page.locator('[data-close]').first.click()
        # A slower first photo decode must not overwrite a newer selected photo.
        await page.evaluate('''() => {window.__pending=[];window.resizePhoto=(file)=>new Promise(resolve=>window.__pending.push(resolve));}''')
        await page.evaluate('''() => {window.__slow=inputPhoto({target:{files:[{type:'image/jpeg',size:100}],value:'old'}});
           window.__fast=inputPhoto({target:{files:[{type:'image/jpeg',size:100}],value:'new'}});}''')
        assert await page.evaluate('window.__pending.length')==2
        await page.evaluate('(im)=>window.__pending[1](im)',detail)
        await page.wait_for_function('(im)=>s.image===im',arg=detail)
        await page.evaluate('(im)=>window.__pending[0](im)',dark)
        await page.evaluate('Promise.all([window.__slow,window.__fast])')
        assert await page.evaluate('s.image')==detail
        assert await page.evaluate('s.cats.length')==1
        assert await page.evaluate('s.profile.xp')==xp
        assert (ROOT/'BrowserPreview/app.js').read_text()==(ROOT/'WhiskerHunt/Resources/Raw/app.js').read_text()
        assert (ROOT/'BrowserPreview/style.css').read_text()==(ROOT/'WhiskerHunt/Resources/Raw/style.css').read_text()
        assert "const CACHE='whisker-hunt-shell-v19'" in (ROOT/'BrowserPreview/sw.js').read_text()
        assert not errors,errors
        print('PASS v1.5: exposure/detail checks, retake/cancel, replacement, no premature saves, repeat-cat intent, latest photo wins')
        await browser.close()

if __name__=='__main__': asyncio.run(main())
