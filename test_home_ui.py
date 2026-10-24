from playwright.sync_api import sync_playwright
from pathlib import Path
import re
folder=Path('/mnt/data/hush_v3112/BrowserPreview')
html=(folder/'index_v75.html').read_text()
html=re.sub(r'<link rel="stylesheet"[^>]*>', '',html)
html=re.sub(r'<script src="app_v75.js" defer></script>', '',html)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
 errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(html,wait_until='domcontentloaded')
 page.add_style_tag(content=(folder/'style_v75.css').read_text())
 page.add_script_tag(content=(folder/'app_v75.js').read_text())
 page.evaluate('render()')
 print('errors:',errors[:5])
 print('title:',page.title())
 print('hero:',page.locator('.hush-immersive-home').count())
 print('buttons:',page.locator('.hush-story-main').count(),'duplicate shortcut row:',page.locator('.hush-story-mini-actions').count())
 print('bottom nav:',page.locator('.bottom-nav [data-nav]').count())
 print('Live BG:',page.locator('#hush-direct-live').evaluate('(el)=>getComputedStyle(el).backgroundImage'))
 print('AR BG:',page.locator('#hush-direct-ar').evaluate('(el)=>getComputedStyle(el).backgroundImage'))
 from base64 import b64encode
 hero=page.locator('.hush-story-hero')
 theme=page.evaluate('hushCurrentTheme74()')
 for key,src in [('--hush-wallpaper','themes_v74/'+theme['id']+'.webp'),('--hush-live-photo',theme['liveArt']),('--hush-ar-photo',theme['arArt'])]:
  uri='data:image/webp;base64,'+b64encode((folder/src).read_bytes()).decode()
  hero.evaluate('(el, pair)=>el.style.setProperty(pair[0], `url("${pair[1]}")`)',[key,uri])
 page.screenshot(path='/mnt/data/hush_v3112/Home_Theme_v75_Preview.png',full_page=True)
 page.locator('#hush-theme-open-home').click()
 print('theme buttons:',page.locator('#hush-theme-dynamic').count(),page.locator('#hush-theme-static').count())
 page.locator('#hush-theme-static').click()
 page.locator('[data-hush-theme-id="blue-morpho-garden"]').click()
 page.locator('#hush-theme-done').click()
 print('static:',page.locator('.hush-story-hero').get_attribute('style'))
 print('errors after interaction:',errors[:5])
 browser.close()
