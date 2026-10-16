"""v0.7 privacy tools: safe export, pin wipe, rollback, legacy backup compatibility."""
import asyncio, io, json
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo():
    im=Image.new('RGB',(100,90),(245,180,90));b=io.BytesIO();im.save(b,format='JPEG');return b.getvalue()

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844},accept_downloads=True)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
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
  await page.locator('#hero-catch').click()
  await page.locator('#library-input').set_input_files({'name':'cat.jpg','mimeType':'image/jpeg','buffer':photo()})
  await page.locator('#encounter-skip').click()  # v1.2+ capture mini-game is optional
  await page.locator('#cat-name').fill('Noodles')
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.wait_for_function('s.cats.length===1 && s.cats[0].sightings.length===1 && !s.busy')
  await page.evaluate('''() => {s.cats[0].sightings[0].lat=51.515;s.cats[0].sightings[0].lng=-0.13;
    s.cats[0].sightings.push({id:'reunion-1',at:new Date().toISOString(),note:'Back again',photo:null,lat:51.517,lng:-0.132});
    s.profile.xp=345;}''')
  assert await page.evaluate('pinnedSightings()')==2
  # A safe backup contains zero GPS coordinates but all cats/sightings/XP.
  safe=await page.evaluate('backupPayload(true)')
  full=await page.evaluate('backupPayload(false)')
  assert full['cats'][0]['sightings'][0]['lat']==51.515
  assert safe['cats'][0]['sightings'][0].get('lat') is None
  assert 'lat' not in safe['cats'][0]['sightings'][0]
  assert 'lng' not in safe['cats'][0]['sightings'][1]
  assert safe['profile']['xp']==345 and len(safe['cats'][0]['sightings'])==2
  assert await page.evaluate('pinnedSightings()')==2
  await page.locator('#head-profile').click()
  await page.locator('[data-action="privacy-tools"]').click()
  assert await page.get_by_text('2 location pins',exact=True).is_visible()
  await page.screenshot(path=str(ROOT/'tests'/'v07-privacy-tools.png'),full_page=True)
  async with page.expect_download() as download_info:
   await page.locator('#export-safe').click()
  download=await download_info.value
  assert 'gps-free-backup' in download.suggested_filename
  exported=json.loads((await download.path()).read_text())
  assert exported['profile']['xp']==345
  assert len(exported['cats'][0]['sightings'])==2
  assert all('lat' not in v and 'lng' not in v for v in exported['cats'][0]['sightings'])
  # The safe export is a separate copy, not a destructive local mutation.
  assert await page.evaluate('pinnedSightings()')==2
  # Failure path: no in-memory changes if IndexedDB transaction fails.
  await page.evaluate('''() => {window._persistCatsAtomic=persistCatsAtomic;persistCatsAtomic=()=>Promise.reject(Error('Simulated quota error'))}''')
  await page.locator('#forget-all-pins').click()
  assert await page.evaluate('pinnedSightings()')==2
  assert await page.get_by_text('Your original pins were kept.',exact=False).is_visible()
  await page.evaluate('() => {persistCatsAtomic=window._persistCatsAtomic}')
  await page.locator('#forget-all-pins').click()
  await page.wait_for_function('pinnedSightings()===0 && !s.busy')
  assert await page.evaluate('s.profile.xp')==345
  assert await page.evaluate('s.cats[0].sightings.length')==2
  assert await page.evaluate('window.__cats.get(s.cats[0].id).sightings.every(x=>x.lat===undefined&&x.lng===undefined)')
  assert await page.evaluate('backupPayload().cats[0].sightings.every(x=>x.lat===undefined&&x.lng===undefined)')
  # A GPS-free v1 backup remains importable, preserving XP and no location fields.
  await page.evaluate('(b)=>loadBackupText(JSON.stringify(b))',safe)
  assert await page.evaluate('s.cats[0].sightings.length')==2
  assert await page.evaluate('s.profile.xp')==345
  assert not errors,errors
  print('PASSED v0.7: GPS-free export, local pins unchanged, atomic wipe, rollback on storage failure, XP/cats preserved, legacy restore')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
