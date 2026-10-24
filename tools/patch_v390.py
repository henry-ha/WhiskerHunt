from pathlib import Path
from shutil import copy2
root=Path(__file__).resolve().parents[1]
for p in (root/'BrowserPreview/app.js',root/'BrowserPreview/app_v52.js',root/'WhiskerHunt/Resources/Raw/app.js',root/'WhiskerHunt/Resources/Raw/app_v52.js'):
 t=p.read_text(encoding='utf-8')
 t=t.replace("const WHISKER_BUILD='3.8.9', WHISKER_BUILD_NUMBER=53;","const WHISKER_BUILD='3.9.0', WHISKER_BUILD_NUMBER=54;")
 t=t.replace("const supported=hasAndroidActionBridge();\n openModal(`", "const supported=hasAndroidActionBridge();\n openModal(`")
 t=t.replace('${supported?\'\':\'disabled\'}','')
 t=t.replace(" if(supported)$('hush-arcore-start').onclick=hushLaunchArCore;", " $('hush-arcore-start').onclick=hushLaunchArCore;")
 t=t.replace("if(!hasAndroidActionBridge())return hushOriginalStartArEncounter();", """if(!hasAndroidActionBridge()){
  openModal('<div class="sheet-head"><h2>ARCore needs the Android app</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">Real-world surface tracking only works in the installed Android version of Hush Hunt. The browser demo supports 2D Safari instead.</p><div class="actions"><button type="button" class="primary" id="hush-ar-use-2d">✨ Try 2D Safari</button></div>');
  $('hush-ar-use-2d').onclick=hushOriginalStartArEncounter;return;
 }""")
 t=t.replace("Native ARCore can only start inside the installed Android app.'}","Tap to try ARCore on your device; the Android app will tell you if AR services need installing.'}")
 # remove cosmetic variant badge/tint in favour of accurately different images
 old=""" const accent=fieldGuideAccent(group,name);
 const badge=kind==='group'?'':`<span class="field-guide-art-badge" style="background:${accent.badge}">${esc(accent.code)}</span>`;
 const tint=kind==='group'?'':`<span class="field-guide-art-tint" style="background:${accent.tint}"></span>`;
 return `<button type="button" class="field-guide-tile ${kind==='group'?'field-guide-tile-group':''} ${isSelected?'chosen':''}" ${action}="${esc(name)}" aria-pressed="${isSelected?'true':'false'}" aria-label="${esc(name)}"><span class="field-guide-figure"><img src="${esc(img)}" loading="lazy" alt="" width="84" height="84">${tint}${badge}</span><span>${esc(name)}</span>${isSelected?'<span class="visual-tile-check" aria-hidden="true">✓</span>':''}</button>`;
"""
 new=""" return `<button type="button" class="field-guide-tile ${kind==='group'?'field-guide-tile-group':''} ${isSelected?'chosen':''}" ${action}="${esc(name)}" aria-pressed="${isSelected?'true':'false'}" aria-label="${esc(name)}"><span class="field-guide-figure"><img src="${esc(img)}" loading="lazy" alt="" width="110" height="110"></span><span>${esc(name)}</span>${isSelected?'<span class="visual-tile-check" aria-hidden="true">✓</span>':''}</button>`;
"""
 if old not in t:
  print('WARNING old tile missing',p)
 else:t=t.replace(old,new)
 p.write_text(t,encoding='utf-8')

for p in (root/'BrowserPreview/style.css',root/'BrowserPreview/style_v52.css',root/'WhiskerHunt/Resources/Raw/style.css',root/'WhiskerHunt/Resources/Raw/style_v52.css'):
 t=p.read_text(encoding='utf-8')
 t=t.replace('height:92px;object-fit:cover;','height:112px;object-fit:contain;')
 t=t.replace('height:65px;max-width:88px','height:75px;max-width:88px')
 t += '\n/* v3.9.0 illustrations: preserve individual animal silhouettes, not badge overlays */\n.field-guide-figure{display:flex;align-items:center;justify-content:center;overflow:hidden;border-radius:12px}\n.field-guide-art-badge,.field-guide-art-tint{display:none!important}\n.field-guide-tile img{height:112px;object-fit:contain;max-width:130px}\n.field-guide-tile-group img{height:75px;max-width:88px}\n.brand-icon img{display:block;width:42px;height:42px;object-fit:cover;border-radius:12px}\n'
 p.write_text(t,encoding='utf-8')

for p in (root/'BrowserPreview/index.html',root/'BrowserPreview/index_v52.html',root/'WhiskerHunt/Resources/Raw/index.html',root/'WhiskerHunt/Resources/Raw/index_v52.html'):
 t=p.read_text(encoding='utf-8')
 t=t.replace('3.8.9-53','3.9.0-54')
 t=t.replace('href="icon.svg"','href="icon-192.png"').replace('type="image/svg+xml" href="icon-192.png"','type="image/png" href="icon-192.png"')
 t=t.replace('<span class="brand-icon">🧭</span>','<span class="brand-icon"><img src="icon-192.png" alt="Hush Hunt" width="42" height="42"></span>')
 t=t.replace('href="style_v52.css"','href="style_v54.css"')
 t=t.replace('src="app_v52.js"','src="app_v54.js"')
 p.write_text(t,encoding='utf-8')

for d in (root/'BrowserPreview',root/'WhiskerHunt/Resources/Raw'):
 copy2(d/'app.js',d/'app_v54.js')
 copy2(d/'style.css',d/'style_v54.css')
 copy2(d/'index_v52.html',d/'index_v54.html')
 # entrypoint is coherent for browser and native, native keeps its known bridge marker

p=root/'WhiskerHunt/MainPage.xaml'
t=p.read_text().replace('Source="index_v52.html"','Source="index_v54.html"')
p.write_text(t)
print('UI/AR patches complete')
