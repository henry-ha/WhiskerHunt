"""Hush Hunt v3.9.0 build 54 offline art and ARCore enablement smoke test."""
import asyncio,hashlib,re,json
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def check_assets():
 browser=ROOT/'BrowserPreview'; android=ROOT/'WhiskerHunt/Resources/Raw'
 js=(browser/'app_v54.js').read_text()
 catalog=json.loads(re.search(r'const FIELD_GUIDE_VARIETIES=(\{.*?\});',js).group(1))
 assert len(catalog)==17 and sum(map(len,catalog.values()))==128
 all_hashes=set()
 for group,types in catalog.items():
  group_hashes=set()
  for name in types:
   filename=re.sub(r'[^a-z0-9]+','-',group.lower()).strip('-')+'-'+re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')+'.webp'
   a=browser/'field_art'/filename; b=android/'field_art'/filename
   assert a.is_file() and a.read_bytes()==b.read_bytes(), filename
   with Image.open(a) as im: assert im.width==im.height==240,filename
   h=hashlib.sha256(a.read_bytes()).digest();group_hashes.add(h);all_hashes.add(h)
  assert len(group_hashes)==len(types),group
 assert len(all_hashes)==128
 assert (ROOT/'WhiskerHunt/Resources/AppIcon/appicon.png').is_file()
 assert 'Resources\\AppIcon\\appicon.png' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert '<ApplicationVersion>54</ApplicationVersion>' in (ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
 assert 'index_v54.html' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
 assert 'WhiskerHunt.sln' in [p.name for p in ROOT.iterdir()]
 assert b'<script>window.whiskerNativeBridge=true;</script>' in (android/'index_v54.html').read_bytes()
 assert (browser/'app_v54.js').read_bytes()==(android/'app_v54.js').read_bytes()
 assert (browser/'style_v54.css').read_bytes()==(android/'style_v54.css').read_bytes()
 assert '<span class="brand-icon"><img src="icon-192.png"' in (browser/'index_v54.html').read_text()
 assert '<span class="brand-icon"><img src="icon-192.png"' in (android/'index_v54.html').read_text()
 assert 'Could not open ARCore Safari' in (ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
 return sum(map(len,catalog.values()))

async def main():
 n=check_assets()
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'BrowserPreview/index_v54.html').read_text()
  html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
  html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style_v54.css').read_text())
  await page.add_script_tag(content=(ROOT/'BrowserPreview/app_v54.js').read_text())
  await page.wait_for_function('typeof hushChooseArSafari==="function" && typeof FIELD_GUIDE_VARIETIES!=="undefined"',timeout=25000)
  await page.evaluate('hushChooseArSafari()')
  button=page.locator('#hush-arcore-start')
  assert await button.is_enabled(), 'ARCore button must NOT be greyed out'
  await button.click()
  assert 'ARCore needs the Android app' in await page.locator('#modal-layer').inner_text()
  await page.locator('#hush-ar-use-2d').count()==1
  await page.evaluate('closeModal();window.whiskerNativeBridge=true;hushChooseArSafari()')
  assert await page.locator('#hush-arcore-start').is_enabled()
  assert not errors,errors
  await browser.close()
 print(f'PASS v3.9.0: {n} unique variety images, offline Android/browser parity, launcher icon, ARCore option enabled in Safari, browser guidance, unchanged collection ID')

if __name__=='__main__':asyncio.run(main())
