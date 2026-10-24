"""Source + browser checks for approved Hush Hunt branding and transparent Safari overlays."""
from pathlib import Path
from PIL import Image
import hashlib,re,json,asyncio
from playwright.async_api import async_playwright
R=Path(__file__).resolve().parents[1];N=R/'WhiskerHunt';raw=N/'Resources/Raw';web=R/'BrowserPreview'
cs=(N/'WhiskerHunt.csproj').read_text()
assert '<ApplicationDisplayVersion>3.10.0</ApplicationDisplayVersion>' in cs
assert '<ApplicationVersion>63</ApplicationVersion>' in cs
assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in cs
assert 'hushhunt_bunny_v63.png' in cs and 'hushhunt_bunny_splash_v63.png' in cs
assert 'Source="index_v63.html"' in (N/'MainPage.xaml').read_text()
assert 'hushhunt_launcher' in (N/'Platforms/Android/AndroidManifest.xml').read_text()
assert Image.open(N/'Resources/AppIcon/hushhunt_bunny_v63.png').size==(1024,1024)
assert Image.open(N/'Resources/Splash/hushhunt_bunny_splash_v63.png').size==(512,512)
for size,density in ((48,'mdpi'),(72,'hdpi'),(96,'xhdpi'),(144,'xxhdpi'),(192,'xxxhdpi')):
 for kind in ('hushhunt_launcher.png','hushhunt_launcher_round.png'):
  assert Image.open(N/f'Platforms/Android/Resources/mipmap-{density}'/kind).size==(size,size)
for b in (web,raw):
 assert 'app_v63.js' in (b/'index_v63.html').read_text()
 assert 'style_v63.css' in (b/'index_v63.html').read_text()
 assert '3.10.0-63' in (b/'index_v63.html').read_text()
 assert (b/'app.js').read_bytes()==(b/'app_v63.js').read_bytes()
 assert 'safariCreatureArt(group,m.speciesDetail)' in (b/'app.js').read_text()
 assert 'ctx.drawImage(cat,x-185,y-185,370,370)' in (b/'app.js').read_text()
 sprites=list((b/'safari_cutouts_v63').glob('*.png'))
 assert len(sprites)==146, len(sprites)
 for p in sprites:
  with Image.open(p) as img:
   assert img.mode=='RGBA' and img.getextrema()[3][0]==0,p
   assert img.getextrema()[3][1]==255,p
 assert len(list((b/'field_art_v62').glob('*.webp')))==146
for f in (raw/'safari_cutouts_v63').glob('*.png'):
 assert hashlib.sha256(f.read_bytes()).digest()==hashlib.sha256((web/'safari_cutouts_v63'/f.name).read_bytes()).digest()
for p in (N/'MainPage.xaml.cs',N/'Platforms/Android/HushArCoreActivity.cs'):
 code=p.read_text();assert r'safari_cutouts_v63/[a-z0-9-]+\.png' in code
assert 'whisker-hunt-state.json' in (N/'MainPage.xaml.cs').read_text()
async def browser():
 async with async_playwright() as p:
  chromium=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  page=await chromium.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(web/'index_v63.html').read_text()
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(web/'style_v63.css').read_text())
  await page.add_script_tag(content=(web/'app_v63.js').read_text())
  await page.evaluate('boot()')
  await page.wait_for_function('window.whiskerBootComplete === true')
  assert await page.evaluate("safariCreatureArt('Snail','Garden Snail')")=='safari_cutouts_v63/snail-garden-snail.png'
  assert await page.evaluate("fieldGuideArt('Snail','Garden Snail')")=='field_art_v62/snail-garden-snail.webp'
  await page.evaluate('hushChooseArSafari()')
  assert await page.locator('#hush-arcore-start').count()==1
  assert await page.locator('#hush-ar-2d').count()==1
  assert not errors,errors
  await chromium.close()
asyncio.run(browser())
print('PASS v63 approved launcher+splash+header, 146 transparent native/browser sprite paths, collection art preserved, Safari JS browser smoke, app ID unchanged')
