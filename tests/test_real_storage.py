"""Real IndexedDB persistence smoke test using localhost Chromium (not mocked)."""
import asyncio,io,subprocess,time,socket
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
async def main():
 sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
 proc=subprocess.Popen(['python','-m','http.server',str(port),'--bind','127.0.0.1'],cwd=ROOT/'BrowserPreview',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  async with async_playwright() as p:
   browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   context=await browser.new_context(viewport={'width':390,'height':844})
   page=await context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   await page.goto(f'http://127.0.0.1:{port}',wait_until='networkidle');await page.wait_for_function('window.whiskerBootComplete')
   img=Image.new('RGB',(360,300),(180,140,110));d=ImageDraw.Draw(img);d.ellipse((90,40,300,270),fill=(120,110,90));b=io.BytesIO();img.save(b,format='JPEG')
   await page.locator('#hero-catch').click()
   await page.locator('#library-input').set_input_files({'name':'real.jpg','mimeType':'image/jpeg','buffer':b.getvalue()})
   await page.locator('#cat-name').fill('Persisted Cat');await page.locator('#real-cat').check();await page.locator('#save-catch').click()
   await page.locator('.cat-tile').first.wait_for()
   assert await page.evaluate('s.profile.xp')==125
   await page.reload(wait_until='networkidle');await page.wait_for_function('window.whiskerBootComplete')
   assert await page.evaluate('s.cats.length')==1
   assert await page.evaluate('s.profile.xp')==125
   assert await page.evaluate('s.cats[0].name')=='Persisted Cat'
   assert not errors,errors
   print('PASSED real Chromium IndexedDB create + XP atomic save + reload')
   await browser.close()
 finally:proc.terminate();proc.wait(timeout=5)
if __name__=='__main__':asyncio.run(main())
