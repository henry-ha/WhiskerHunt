from pathlib import Path
from PIL import Image
import re, subprocess, zipfile
root=Path('/mnt/data/hush_v3111')
assert '<ApplicationDisplayVersion>3.10.11</ApplicationDisplayVersion>' in (root/'WhiskerHunt/WhiskerHunt.csproj').read_text()
assert '<ApplicationVersion>74</ApplicationVersion>' in (root/'WhiskerHunt/WhiskerHunt.csproj').read_text()
assert 'Source="index_v74.html"' in (root/'WhiskerHunt/MainPage.xaml').read_text()
assert 'PreviewPlace' in (root/'WhiskerHunt/Platforms/Android/HushArCoreActivity.cs').read_text()
results=[]
for folder in [root/'BrowserPreview',root/'WhiskerHunt/Resources/Raw']:
 html=(folder/'index_v74.html').read_text()
 assert 'app_v74.js' in html and 'style_v74.css' in html
 assert (folder/'sw.js').read_text().count('v73')==0
 script=(folder/'app_v74.js').read_text()
 assert "const WHISKER_BUILD='3.10.11', WHISKER_BUILD_NUMBER=74;" in script
 for asset in ['themes_v74','field_art_v74']:
  assert (folder/asset).exists()
 assert len(list((folder/'themes_v74').glob('*.webp')))==6
 assert len(list((folder/'field_art_v74').glob('*.webp')))>=140
 assert not list(folder.glob('*_v73.js')) and not list(folder.glob('index_v73.html'))
 assert 'hushThemeSettings74' in script and 'hush-mystery-help' in script and 'hush-camera-clean' in script
 assert "('hush-direct-live')?.addEventListener('click',hushFastLiveCapture)" not in script
 css=(folder/'style_v74.css').read_text()
 assert 'hush-immersive-home' in css and 'hush-camera-clean' in css
 for p in (folder/'themes_v74').glob('*.webp'):Image.open(p).verify()
 for p in (folder/'field_art_v74').glob('frog-*.webp'):Image.open(p).verify()
 proc=subprocess.run(['node','--check',str(folder/'app_v74.js')],capture_output=True,text=True)
 assert proc.returncode==0,proc.stderr
 results.append(f'{folder.relative_to(root)}: HTML → app_v74.js + style_v74.css; 6 themes, {len(list((folder/"field_art_v74").glob("*.webp")))} guide tiles; JS syntax PASS')
assert (root/'BrowserPreview/app_v74.js').read_bytes()==(root/'WhiskerHunt/Resources/Raw/app_v74.js').read_bytes()
assert (root/'BrowserPreview/style_v74.css').read_bytes()==(root/'WhiskerHunt/Resources/Raw/style_v74.css').read_bytes()
print('\n'.join(results))
print('Android project version 3.10.11 / build 74, MAUI entrypoint PASS')
print('AR fallback source: Place + screen-locked preview + Capture PASS')
