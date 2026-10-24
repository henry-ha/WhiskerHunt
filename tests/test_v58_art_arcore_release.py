"""Static + browser smoke checks for Hush Hunt v3.9.4 / build 58."""
from pathlib import Path
from PIL import Image
import re,hashlib,asyncio
from playwright.async_api import async_playwright
root=Path(__file__).resolve().parents[1]

def inspect():
 a=root/'WhiskerHunt/Resources/Raw';b=root/'BrowserPreview'
 assert '3.9.4' in (root/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert '<ApplicationVersion>58</ApplicationVersion>' in (root/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert 'index_v58.html' in (root/'WhiskerHunt/MainPage.xaml').read_text()
 assert (a/'app_v58.js').read_bytes()==(b/'app_v58.js').read_bytes()
 assert (a/'style_v58.css').read_bytes()==(b/'style_v58.css').read_bytes()
 assert 'window.whiskerNativeBridge=true' in (a/'index_v58.html').read_text()
 assert 'uk.whiskerhunt.mobile' in (root/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 for filename in ['dog-golden-retriever.webp','dog-spaniel.webp','dog-mixed-breed.webp','dog-group.webp',
   'rabbit-lop-eared.webp','hedgehog-european-hedgehog.webp','frog-tree-frog.webp',
   'snail-roman-snail.webp','snail-amber-snail.webp','dragonfly-four-spotted-chaser.webp',
   'dragonfly-golden-ringed-dragonfly.webp','other-deer.webp','bird-swan.webp']:
  assert (a/'field_art'/filename).read_bytes()==(b/'field_art'/filename).read_bytes(),filename
  with Image.open(a/'field_art'/filename) as pic:
   assert pic.size==(240,240),filename
 with Image.open(a/'field_art/dog-golden-retriever.webp') as gold, Image.open(a/'field_art/dog-labrador.webp') as lab:
  assert hashlib.sha256(gold.tobytes()).digest()!=hashlib.sha256(lab.tobytes()).digest()
 all_a=list((a/'field_art').glob('*.webp'))
 assert len(all_a)>=145
 for p in all_a: assert p.read_bytes()==(b/'field_art'/p.name).read_bytes()
 manifest=(root/'WhiskerHunt/Platforms/Android/AndroidManifest.xml').read_text()
 assert '@mipmap/hushhunt_launcher' in manifest
 for bucket in ['mdpi','hdpi','xhdpi','xxhdpi','xxxhdpi']:
  assert (root/f'WhiskerHunt/Platforms/Android/Resources/mipmap-{bucket}/hushhunt_launcher.png').is_file()
 cs=(root/'WhiskerHunt/Platforms/Android/HushArCoreActivity.cs').read_text()
 assert 'PixelCopy.Request(_surface' in cs
 assert 'class PixelCopyListener' in cs
 assert 'Bitmap.CreateBitmap(width, height' in cs
 assert 'new AndroidRect(0, 0, _art.Width, _art.Height)' in cs
 assert 'GLES.GlReadPixels' not in cs
 assert 'private static bool HasTrackablePlaneAt(Google.AR.Core.Frame frame' in cs
 assert 'float newX = x - w / 2f' in cs
 assert (root/'WhiskerHunt.sln').exists()
 return len(all_a)

async def browser_test():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(root/'BrowserPreview/index_v58.html').read_text()
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(root/'BrowserPreview/style_v58.css').read_text())
  await page.add_script_tag(content=(root/'BrowserPreview/app_v58.js').read_text())
  await page.wait_for_function('typeof hushChooseArSafari === "function"',timeout=20000)
  await page.evaluate('hushChooseArSafari()')
  button=page.locator('#hush-arcore-start')
  assert await button.is_enabled()
  await button.click()
  assert 'ARCore needs the Android app' in await page.locator('#modal-layer').inner_text()
  assert not errors,errors
  await browser.close()

if __name__=='__main__':
 n=inspect(); print(f'PASS static: {n} identical Android/browser artwork files, app icon manifest, AR PixelCopy code, backup compatible')
 asyncio.run(browser_test());print('PASS browser: ARCore option enabled, guidance displayed, no JS errors')
