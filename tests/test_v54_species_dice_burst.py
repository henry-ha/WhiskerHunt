"""Hush Hunt 3.9.0: species dice, more live burst frames, visual naming and compatibility."""
import asyncio,re
from pathlib import Path
from playwright.async_api import async_playwright
R=Path(__file__).resolve().parents[1]
async def main():
 b=R/'BrowserPreview'; raw=R/'WhiskerHunt/Resources/Raw'
 assert '<ApplicationVersion>54</ApplicationVersion>' in (R/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in (R/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert 'index_v54.html' in (R/'WhiskerHunt/MainPage.xaml').read_text()
 assert 'window.whiskerNativeBridge=true;' in (raw/'index_v54.html').read_text()
 assert (b/'app_v54.js').read_bytes()==(raw/'app_v54.js').read_bytes()
 assert (b/'style_v54.css').read_bytes()==(raw/'style_v54.css').read_bytes()
 assert (b/'sw.js').read_bytes()==(raw/'sw.js').read_bytes()
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',(b/'index.html').read_text())
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(b/'style_v54.css').read_text())
  await page.add_script_tag(content=(b/'app_v54.js').read_text())
  await page.evaluate('''()=>{window.__cats=new Map();window.__meta=new Map();window.openDb=async()=>({mock:true,transaction:()=>{const tx={objectStore:store=>({put:value=>{const m=store==='cats'?window.__cats:window.__meta;m.set(store==='cats'?value.id:value.key,value)}})};setTimeout(()=>tx.oncomplete?.(),0);return tx}});window.transact=async(store,mode,method,value)=>{const m=store==='cats'?window.__cats:window.__meta;if(method==='getAll')return [...m.values()];if(method==='get')return m.get(value);if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value}};boot()}''')
  await page.wait_for_function('window.whiskerBootComplete===true')
  assert 'Collection' in await page.locator('[data-nav=dex]').inner_text()
  await page.evaluate("navigate('dex')")
  assert 'Collection' in (await page.locator('#view').inner_text())
  assert await page.evaluate('LIVE_FRAME_MAX')==12
  assert await page.evaluate('LIVE_SAMPLE_INTERVAL')==260
  assert await page.evaluate('LIVE_CAPTURE_SIZE')==960
  assert await page.evaluate('rankLiveFramesAtFocus.toString().includes("slice(-12)")')
  # All non-cat categories have safe, non-cat-only dice prompts.
  assert await page.evaluate('Object.keys(HUSH_DICE_NAMES).length')==17
  for group in ['Snail','Butterfly','Bird','Dog','Ant','Rabbit','Hedgehog','Other']:
   pair=await page.evaluate('''g=>[hushRollName(g),hushRollMemory(g)]''',group)
   assert all(pair)
   if group!='Cat':assert not any(v in pair[1].lower() for v in ['whisker','kitty','cat looked','tiny paws'])
  # Real sighting form provenance is protected, even though this uses a synthetic camera shot.
  # Test visual dice at the current form; do not bypass the actual save/verification handlers.
  tiny='data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAL/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwD/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAEFAq//2Q=='
  await page.evaluate('''img=>{s.realLiveProof={ready:true,images:new Set([img])};s.image=img;s.encounterLive=true;s.encounterAr=false;s.wildTarget='Snail';showCatForm(img)}''',tiny)
  assert await page.locator('#wildlife-species').count()==1
  assert await page.locator('#wildlife-species').input_value()=='Snail'
  assert await page.locator('#dice-name').count()==1
  await page.locator('#dice-name').click()
  assert await page.locator('#cat-name').input_value()
  await page.locator('#dice-memory').click()
  memory=await page.locator('#cat-note').input_value()
  assert memory and 'whisker' not in memory.lower() and 'kitty' not in memory.lower()
  await page.locator('#wildlife-species').select_option('Butterfly')
  # Force species-only pool to confirm current dropdown changes dice behaviour.
  await page.evaluate('Math.random=()=>0')
  await page.locator('#dice-memory').click()
  butterfly_memory=await page.locator('#cat-note').input_value()
  assert butterfly_memory in await page.evaluate('HUSH_DICE_SPECIES_MEMORIES.Butterfly')
  # At most five reviewed frames, no videos, existing collection remains untouched.
  await page.evaluate('''img=>{openModal('<div id="encounter-shots"></div><img id="encounter-photo"/><div id="encounter-quality"></div>');const q={label:'Okay',score:70};displayCaptureShotChoices(Array.from({length:12},(_,i)=>({image:img,quality:q,subjectQuality:q,at:i})));}''',tiny)
  assert await page.locator('.shot-option').count()==5
  assert await page.evaluate('captureShots.length')==5
  assert await page.evaluate('s.cats.length')==0
  assert await page.evaluate('JSON.stringify(backupPayload()).includes("captureShots")') is False
  assert not errors,errors
  await browser.close()
 print('PASS v3.9.0 species-specific dice UI, 17 groups, burst buffers, five-shot chooser, collection label, backup compatibility, Android/browser assets')
if __name__=='__main__':asyncio.run(main())
