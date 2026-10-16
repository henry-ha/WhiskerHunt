"""Whisker Hunt v0.5: focused regression tests for safe restore, sorting and catch rollback."""
import asyncio,base64,io,json
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def photo(colour):
 im=Image.new('RGB',(360,300),colour);d=ImageDraw.Draw(im)
 d.ellipse((80,40,290,270),fill=(180,160,130));d.ellipse((125,130,145,160),fill='black');d.ellipse((225,130,245,160),fill='black')
 b=io.BytesIO();im.save(b,format='JPEG');return b.getvalue()

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  ctx=await browser.new_context(viewport={'width':390,'height':844})
  page=await ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
  await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
  await page.evaluate('''() => {
   window.__cats=new Map();window.__meta=new Map();
   window.openDb=async()=>({transaction:(stores,mode)=>{
    const tx={objectStore:(store)=>({put:(v)=>{(store==='cats'?window.__cats:window.__meta).set(store==='cats'?v.id:v.key,v)}})};
    setTimeout(()=>tx.oncomplete?.(),0);return tx;
   }});
   window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;
    if(method==='getAll')return Array.from(m.values());if(method==='get')return m.get(value);
    if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}
    if(method==='delete')m.delete(value);
   };boot();window.confirm=()=>true;
  }''')
  await page.wait_for_function('window.whiskerBootComplete')
  async def catch(name,colour):
   await page.locator('#nav-catch').click()
   await page.locator('#library-input').set_input_files({'name':name+'.jpg','mimeType':'image/jpeg','buffer':photo(colour)})
   await page.locator('#encounter-skip').click()  # v1.2+ capture mini-game is optional
   await page.locator('#cat-name').fill(name)
   await page.locator('#real-cat').check()
   await page.locator('#save-catch').click()
   await page.locator('#modal-layer').wait_for(state='hidden')
  await catch('Ziggy',(100,150,220))
  await catch('Amber',(220,120,90))
  assert await page.evaluate('s.cats.length')==2
  assert await page.evaluate('s.profile.xp')==225,await page.evaluate('s.profile.xp') # both Tabby, one coat bonus
  await page.locator('#dex-sort').select_option('name')
  assert await page.locator('.cat-tile strong').all_text_contents()==['Amber','Ziggy']
  await page.locator('#dex-sort').select_option('recent')
  assert await page.locator('.cat-tile strong').all_text_contents()==['Amber','Ziggy']
  await page.locator('[data-cat]').filter(has_text='Ziggy').first.click()
  await page.locator('#edit-cat').click()
  await page.locator('#edit-note').fill('Local note must win')
  await page.locator('#edit-save').click()
  await page.locator('[data-close]').first.click()
  # Backup contains an older conflicting cat record and a new sighting.
  backup=await page.evaluate('backupPayload()')
  ziggy=next(c for c in backup['cats'] if c['name']=='Ziggy')
  ziggy['name']='Outdated backup name';ziggy['note']='Outdated backup note'
  ziggy['sightings'][0]['note']='Outdated sighting note'
  ziggy['sightings'].append({'id':'imported-return','at':'2026-10-14T01:00:00Z','note':'Imported reunion','photo':None,'signature':'imported','lat':None,'lng':None})
  backup['cats']=[ziggy]
  backup['profile']['xp']=0
  await page.evaluate('(x)=>loadBackupText(JSON.stringify(x))',backup)
  state=await page.evaluate('''() => ({cats:s.cats.map(c=>({name:c.name,note:c.note,sightings:c.sightings})),xp:s.profile.xp})''')
  assert len(state['cats'])==2,state
  saved=next(c for c in state['cats'] if c['name']=='Ziggy')
  assert saved['note']=='Local note must win',saved
  assert len(saved['sightings'])==2,saved
  assert state['xp']==225,state
  await page.evaluate('(x)=>loadBackupText(JSON.stringify(x))',backup)
  assert await page.evaluate('s.cats.find(c=>c.name==="Ziggy").sightings.length')==2
  await page.locator('[data-close]').first.click() if await page.locator('[data-close]').count() else None
  # A failed atomic write must roll back both the new cat and XP in memory.
  await page.evaluate('() => {window.__realPersist=persistCatchAtomic;persistCatchAtomic=async()=>{throw Error("simulated quota error")};return true}')
  await page.locator('#nav-catch').click()
  await page.locator('#library-input').set_input_files({'name':'failed.jpg','mimeType':'image/jpeg','buffer':photo((40,220,140))})
  await page.locator('#encounter-skip').click()  # v1.2+ capture mini-game is optional
  await page.locator('#cat-name').fill('Failed Cat')
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.get_by_text('Save failed. Please try again.',exact=True).wait_for()
  assert await page.evaluate('s.cats.length')==2
  assert await page.evaluate('s.profile.xp')==225
  assert await page.locator('#save-catch').is_enabled()
  await page.evaluate('() => {persistCatchAtomic=window.__realPersist;return true}')
  await page.locator('[data-close]').first.click()
  await page.locator('#head-profile').click()
  assert await page.locator('.insight-card').count()==4
  assert await page.get_by_text('Adventure days').count()==1
  assert not errors,errors
  await page.screenshot(path=str(ROOT/'tests'/'v05-insights.png'),full_page=True)
  print('PASSED v0.5: sorting, additive restore, idempotence, XP retention, atomic failure rollback, insights')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
