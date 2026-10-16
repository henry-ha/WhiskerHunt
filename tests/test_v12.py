"""v1.2 encounter flow: lure + whisker-ball capture and unchanged save schema."""
import asyncio,base64,io
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(rgb):
 im=Image.new('RGB',(180,140),rgb);buf=io.BytesIO();im.save(buf,format='JPEG')
 return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
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
  im=photo((120,165,205))
  await page.evaluate('(im)=>beginEncounter(im)',im)
  await page.locator('#encounter-stage').wait_for()
  assert await page.get_by_text('Your cat target').count()==1
  await page.locator('#tool-lure').click()
  await page.evaluate('handleEncounterHit("lure")')
  assert await page.evaluate('s.encounterLured') is True
  await page.evaluate('handleEncounterHit("ball")')
  await page.locator('#encounter-continue').wait_for()
  assert await page.get_by_text('You captured this cat!',exact=False).count()>=1
  await page.locator('#encounter-continue').click()
  assert await page.get_by_text('Encounter complete.',exact=False).count()>=1
  assert await page.get_by_text('Photo clarity:',exact=False).count()>=1
  await page.locator('#cat-name').fill('Luna')
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.get_by_text('Luna',exact=True).first.wait_for()
  assert await page.evaluate('s.cats.length')==1
  assert await page.evaluate('s.cats[0].name')=='Luna'
  assert await page.evaluate('s.cats[0].sightings.length')==1
  assert await page.evaluate('s.profile.xp')>=100
  js=(ROOT/'BrowserPreview/app.js').read_text();native=(ROOT/'WhiskerHunt/Resources/Raw/app.js').read_text()
  style=(ROOT/'BrowserPreview/style.css').read_text();native_style=(ROOT/'WhiskerHunt/Resources/Raw/style.css').read_text()
  assert js==native and style==native_style
  assert "const CACHE='whisker-hunt-shell-v22'" in (ROOT/'BrowserPreview/sw.js').read_text()
  assert not errors,errors
  print('PASSED v1.2: lure + whisker-ball encounter, capture summary, unchanged schema, synced assets, current cache')
  await browser.close()

if __name__=='__main__':
 asyncio.run(main())
