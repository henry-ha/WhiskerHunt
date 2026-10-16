"""v0.6 visual-similarity suggestions, manual matching and backup regression."""
import asyncio,io,json,base64
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def cat_photo(variation=0):
 im=Image.new('RGB',(480,400),(120,180,230));d=ImageDraw.Draw(im)
 d.ellipse((100,70,375,355),fill=(185,115,65))
 d.polygon([(130,120),(150,15),(235,105)],fill=(185,115,65))
 d.polygon([(260,100),(325,15),(345,130)],fill=(185,115,65))
 d.ellipse((172,195,195,218),fill=(30,30,30));d.ellipse((285,195,308,218),fill=(30,30,30))
 d.polygon([(226,245),(251,245),(239,262)],fill=(55,35,35))
 if variation:d.rectangle((8,8,22,22),fill=(200,205,220))
 b=io.BytesIO();im.save(b,format='JPEG',quality=88 if variation else 90);return b.getvalue()

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
  await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
  await page.evaluate('''() => {
   window.__cats=new Map();window.__meta=new Map();window.confirm=()=>true;
   window.openDb=async()=>({transaction:()=>{const tx={objectStore:store=>({put:v=>(store==='cats'?window.__cats:window.__meta).set(store==='cats'?v.id:v.key,v)})};setTimeout(()=>tx.oncomplete?.(),0);return tx;}});
   window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;
    if(method==='getAll')return [...m.values()];if(method==='get')return m.get(value);
    if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}
    if(method==='delete')m.delete(value);};boot();
  }''')
  await page.wait_for_function('window.whiskerBootComplete')
  await page.locator('#nav-catch').click()
  await page.locator('#library-input').set_input_files({'name':'cat1.jpg','mimeType':'image/jpeg','buffer':cat_photo()})
  await page.locator('#encounter-skip').click()  # v1.2+ capture mini-game is optional
  await page.locator('#cat-name').fill('Marmalade')
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.locator('.cat-tile').first.wait_for()
  cat=await page.evaluate('s.cats[0]')
  assert len(cat['visualHash'])==16,cat
  assert len(cat['sightings'][0]['visualHash'])==16
  # Simulate a pre-v0.6 cat without a saved fingerprint: lazy matching must work.
  await page.evaluate('s.cats[0].visualHash=null')
  # Two visually near-identical photos, but different bytes, must suggest—not auto-merge.
  await page.locator('#nav-catch').click()
  await page.locator('#library-input').set_input_files({'name':'cat2.jpg','mimeType':'image/jpeg','buffer':cat_photo(1)})
  await page.locator('#encounter-skip').click()  # v1.2+ capture mini-game is optional
  await page.locator('.match-choice').first.wait_for(timeout=12000)
  assert await page.get_by_text('Have you met this cat before?').is_visible()
  await page.locator('.match-notice').scroll_into_view_if_needed()
  await page.wait_for_timeout(4000)
  await page.screenshot(path=str(ROOT/'tests'/'v06-match-suggestion.png'),full_page=True)
  assert await page.locator('#mode-new').evaluate('(x)=>x.classList.contains("selected")')
  assert await page.evaluate('s.cats.length')==1
  await page.locator('.match-choice').first.click()
  assert await page.locator('#mode-repeat').evaluate('(x)=>x.classList.contains("selected")')
  assert await page.locator('#repeat-cat').input_value()==cat['id']
  await page.locator('#repeat-note').fill('Back for a visit')
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.wait_for_function('s.cats.length===1 && s.cats[0].sightings.length===2 && !s.busy')
  assert await page.evaluate('s.cats.length')==1
  assert await page.evaluate('s.cats[0].sightings.length')==2
  assert len(await page.evaluate('s.cats[0].sightings[1].visualHash'))==16
  # Version 1 backup remains backward-compatible; fingerprints are optional.
  backup=await page.evaluate('backupPayload()')
  assert backup['version']==1
  for c in backup['cats']:
   c.pop('visualHash',None)
   for v in c['sightings']:v.pop('visualHash',None)
  await page.evaluate('(b)=>loadBackupText(JSON.stringify(b))',backup)
  assert await page.evaluate('s.cats.length')==1
  assert await page.evaluate('s.cats[0].sightings.length')==2
  assert not errors,errors
  print('PASSED v0.6: visual resemblance hint, explicit manual match, no auto-merge, new hashes, legacy backup restore')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
