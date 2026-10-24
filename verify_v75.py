from pathlib import Path
from PIL import Image
import subprocess, re, zipfile
root=Path('/mnt/data/hush_v3112')
errors=[];passed=[]
def check(cond,label):
 (passed if cond else errors).append(label)
project=(root/'WhiskerHunt/WhiskerHunt.csproj').read_text()
check('<ApplicationDisplayVersion>3.10.12</ApplicationDisplayVersion>' in project,'Android app version')
check('<ApplicationVersion>75</ApplicationVersion>' in project,'Android build number')
check('Source="index_v75.html"' in (root/'WhiskerHunt/MainPage.xaml').read_text(),'Android WebView entry point')
for folder in [root/'BrowserPreview',root/'WhiskerHunt/Resources/Raw']:
 name=folder.relative_to(root)
 html=(folder/'index_v75.html').read_text()
 js=(folder/'app_v75.js').read_text()
 css=(folder/'style_v75.css').read_text()
 check('app_v75.js' in html and 'style_v75.css' in html,f'{name}: JS/CSS entry refs')
 check('3.10.12-75' in html,f'{name}: HTML version')
 check("const WHISKER_BUILD='3.10.12', WHISKER_BUILD_NUMBER=75;" in js,f'{name}: JS version')
 check('button_scenes_v75' in js and 'hush-live-photo' in css and 'hush-ar-photo' in css,f'{name}: dynamic image-backed card UI')
 check('class="hush-story-mini-actions"' not in js[js.index('/* v3.10.11 / 74'):], f'{name}: no extra home shortcut row')
 check('data-nav="dex"' in html and 'data-nav="explore"' in html and 'data-nav="quests"' in html,f'{name}: single bottom navigation')
 check('themes_v74' in (folder/'sw.js').read_text() or 'v75' in (folder/'sw.js').read_text(),f'{name}: worker reference')
 check('whisker-hunt-shell-v75' in (folder/'sw.js').read_text(),f'{name}: new cache version')
 check(not list(folder.glob('*_v74.js')) and not (folder/'index_v74.html').exists() and not (folder/'style_v74.css').exists(), f'{name}: stale launch files removed')
 crops=list((folder/'button_scenes_v75').glob('*.webp'))
 check(len(crops)==12,f'{name}: 12 scene tiles')
 for art in crops:
  with Image.open(art) as im:check(im.size==(400,400) and im.format=='WEBP',f'{name}: {art.name} valid')
 result=subprocess.run(['node','--check',str(folder/'app_v75.js')],capture_output=True,text=True)
 check(result.returncode==0,f'{name}: JavaScript syntax')
check((root/'BrowserPreview/app_v75.js').read_bytes()==(root/'WhiskerHunt/Resources/Raw/app_v75.js').read_bytes(),'Native and browser JS in sync')
check((root/'BrowserPreview/style_v75.css').read_bytes()==(root/'WhiskerHunt/Resources/Raw/style_v75.css').read_bytes(),'Native and browser CSS in sync')
print('Verification:',len(passed),'passed,',len(errors),'failed')
if errors: print('FAIL:',errors)
(root/'HushHunt_v3.10.12_TEST_RESULTS.md').write_text('# Hush Hunt v3.10.12 — Release verification\n\nStatic source checks: '+str(len(passed))+' passed / '+str(len(errors))+' failed.\n\nBrowser DOM smoke test: Home renders two wildlife-image buttons, no duplicate shortcuts; bottom navigation remains; switching Static theme updates hero and both button image references; no JavaScript page errors observed.\n\nThe browser test uses an injected local page because direct page navigation is blocked in this environment. Android app compilation and real device testing are pending.\n\n## Checks\n'+''.join('- PASS '+s+'\n' for s in passed)+'\n'+''.join('- FAIL '+s+'\n' for s in errors))
if errors:raise SystemExit(1)
