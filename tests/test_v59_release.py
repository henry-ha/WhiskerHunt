"""v3.9.5 / build 59 cross-layer integration and visual asset regression checks."""
from pathlib import Path
from PIL import Image
import re, hashlib, asyncio
root=Path(__file__).resolve().parents[1]
raw=root/'WhiskerHunt/Resources/Raw'; web=root/'BrowserPreview'
assert '<ApplicationVersion>59</ApplicationVersion>' in (root/'WhiskerHunt/WhiskerHunt.csproj').read_text()
assert '<ApplicationDisplayVersion>3.9.5</ApplicationDisplayVersion>' in (root/'WhiskerHunt/WhiskerHunt.csproj').read_text()
assert 'uk.whiskerhunt.mobile' in (root/'WhiskerHunt/WhiskerHunt.csproj').read_text()
assert 'index_v59.html' in (root/'WhiskerHunt/MainPage.xaml').read_text()
for p in ['app_v59.js','style_v59.css','sw.js']:
 assert (raw/p).read_bytes()==(web/p).read_bytes(),p
assert 'app_v59.js' in (raw/'index_v59.html').read_text()
assert 'window.whiskerNativeBridge=true' in (raw/'index_v59.html').read_text()
assert 'field_art_v59/' in (root/'WhiskerHunt/MainPage.xaml.cs').read_text()
assert 'field_art_v59/' in (root/'WhiskerHunt/Platforms/Android/HushArCoreActivity.cs').read_text()
assert 'field_art_v59\\/' in (raw/'app_v59.js').read_text()
for name in ['dog-spaniel','snail-roman-snail','snail-amber-snail','snail-other-snail','bird-great-tit','rabbit-lionhead','squirrel-flying-squirrel','hedgehog-long-eared-hedgehog','other-slug','dragonfly-four-spotted-chaser']:
 assert (raw/'field_art_v59'/f'{name}.webp').exists(),name
files=list((raw/'field_art_v59').glob('*.webp'))
assert len(files)>=140,len(files)
for f in files:
 assert f.read_bytes()==(web/'field_art_v59'/f.name).read_bytes(),f.name
 with Image.open(f) as im: assert im.size in ((240,240),(180,180)),(f.name,im.size)
for one,two in [('squirrel-grey-squirrel','squirrel-flying-squirrel'),('squirrel-ground-squirrel','squirrel-red-squirrel'),('rabbit-lop-eared','rabbit-lionhead'),('rabbit-netherland-dwarf','rabbit-flemish-giant'),('hedgehog-african-pygmy-hedgehog','hedgehog-long-eared-hedgehog'),('snail-amber-snail','snail-roman-snail')]:
 assert (raw/'field_art_v59'/f'{one}.webp').read_bytes()!=(raw/'field_art_v59'/f'{two}.webp').read_bytes(),(one,two)
for cat in ['Dog','Cat','Rabbit','Butterfly','Bird','Snail']:
 slug=cat.lower(); path=raw/'field_art_v59'/f'{slug}-group.webp'; assert path.exists(),path
bridge=(root/'WhiskerHunt/MainPage.xaml.cs').read_text()
assert 'Invalid creature selection.' not in bridge
assert r'^field_art_v59/[a-z0-9-]+\.webp$' in bridge
assert r'^field_art_v59/[a-z0-9-]+\.webp$' in (root/'WhiskerHunt/Platforms/Android/HushArCoreActivity.cs').read_text()
assert 'PixelCopy.Request(_surface' in (root/'WhiskerHunt/Platforms/Android/HushArCoreActivity.cs').read_text()
assert (root/'WhiskerHunt.sln').exists()
print('PASS v59 release source: 3-layer AR asset path agreement; %d synchronized artwork assets; no data schema or package rename' % len(files))

async def browser():
 from playwright.async_api import async_playwright
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await b.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(web/'index_v59.html').read_text()
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(web/'style_v59.css').read_text())
  await page.add_script_tag(content=(web/'app_v59.js').read_text())
  await page.wait_for_function('typeof hushChooseArSafari === "function"')
  await page.evaluate('hushChooseArSafari()')
  assert await page.locator('#hush-arcore-start').is_enabled()
  await page.locator('#hush-arcore-start').click()
  assert 'ARCore needs the Android app' in await page.locator('#modal-layer').inner_text()
  assert not errors,errors
  await b.close()
 print('PASS v59 browser: AR Safari button enabled and correctly guided outside Android')

if __name__=='__main__':
 asyncio.run(browser())
