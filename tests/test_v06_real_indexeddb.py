"""Real IndexedDB persistence without localhost server: Playwright HTTPS route fulfillment."""
import asyncio,io
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]/'BrowserPreview'
MIMES={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.webmanifest':'application/manifest+json'}

def photo():
 im=Image.new('RGB',(400,300),'#88bbff');d=ImageDraw.Draw(im);d.ellipse((80,30,320,280),fill='#c08755');b=io.BytesIO();im.save(b,format='JPEG');return b.getvalue()

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  context=await browser.new_context(viewport={'width':390,'height':844},service_workers='block')
  page=await context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  async def serve(route):
   rel=route.request.url.split('https://whisker.test/',1)[-1].split('?',1)[0] or 'index.html'
   file=(ROOT/rel).resolve()
   if not file.is_relative_to(ROOT.resolve()) or not file.is_file():return await route.fulfill(status=404,body='Not found')
   await route.fulfill(status=200,content_type=MIMES.get(file.suffix,'application/octet-stream'),body=file.read_bytes())
  await page.route('https://whisker.test/**',serve)
  await page.goto('https://whisker.test/')
  await page.wait_for_function('window.whiskerBootComplete')
  assert await page.evaluate('s.db instanceof IDBDatabase')
  await page.locator('#nav-catch').click()
  await page.locator('#library-input').set_input_files({'name':'p.jpg','mimeType':'image/jpeg','buffer':photo()})
  await page.locator('#cat-name').fill('Storage Cat')
  await page.locator('#real-cat').check()
  await page.locator('#save-catch').click()
  await page.locator('.cat-tile').first.wait_for()
  xp=await page.evaluate('s.profile.xp')
  await page.reload()
  await page.wait_for_function('window.whiskerBootComplete')
  assert await page.evaluate('s.cats.length')==1
  assert await page.evaluate('s.cats[0].name')=='Storage Cat'
  assert await page.evaluate('s.profile.xp')==xp
  assert await page.evaluate('s.cats[0].visualHash')
  assert not errors,errors
  print('PASSED v0.6 real IndexedDB: save, reload, cat/photo hash and XP survive restart')
  await browser.close()
if __name__=='__main__':asyncio.run(main())
