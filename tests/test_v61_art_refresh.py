"""Regression: v3.9.8 fresh artwork paths match native bridge and don't touch user data."""
from pathlib import Path
import hashlib, re
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
ANDROID=ROOT/'WhiskerHunt/Resources/Raw'
WEB=ROOT/'BrowserPreview'
PROJECT=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
assert '<ApplicationVersion>61</ApplicationVersion>' in PROJECT
assert '<ApplicationDisplayVersion>3.9.8</ApplicationDisplayVersion>' in PROJECT
assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in PROJECT
assert 'index_v61.html' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
for root in (ANDROID,WEB):
    html=(root/'index_v61.html').read_text()
    assert 'app_v61.js' in html and 'style_v61.css' in html
    assert '3.9.8-61' in html
    js=(root/'app_v61.js').read_text()
    assert 'field_art_v61/' in js
    assert 'field_art_v59/' not in js
    assert 'WHISKER_BUILD_NUMBER=61' in js
    assets=list((root/'field_art_v61').glob('*.webp'))
    assert len(assets)==146,len(assets)
    for a in assets:
        with Image.open(a) as image: assert image.size in {(240,240),(180,180)}, (a.name,image.size)
assert (ANDROID/'app_v61.js').read_bytes()==(WEB/'app_v61.js').read_bytes()
assert (ANDROID/'style_v61.css').read_bytes()==(WEB/'style_v61.css').read_bytes()
for a in (ANDROID/'field_art_v61').glob('*.webp'):
    assert hashlib.sha256(a.read_bytes()).digest()==hashlib.sha256((WEB/'field_art_v61'/a.name).read_bytes()).digest(),a.name
# The native bridge, native renderer and JS launcher must agree on the NEW directory.
for path in [ROOT/'WhiskerHunt/MainPage.xaml.cs',ROOT/'WhiskerHunt/Platforms/Android/HushArCoreActivity.cs']:
    code=path.read_text()
    assert r'^field_art_v61/[a-z0-9-]+\.webp$' in code
    assert 'field_art_v59' not in code
assert 'field_art_v61\\/' in (ANDROID/'app_v61.js').read_text()
# New images are a new URL even when old file contents are present in the package.
assert (ANDROID/'field_art_v59/cat-tabby.webp').exists()
assert (ANDROID/'field_art_v61/cat-tabby.webp').exists()
assert (ANDROID/'field_art_v59/cat-tabby.webp').read_bytes()==(ANDROID/'field_art_v61/cat-tabby.webp').read_bytes()
assert 'whisker-hunt-shell-v61' in (WEB/'sw.js').read_text()
assert 'whiskerhunt_local_v1' in (ANDROID/'app_v61.js').read_text()
assert 'whisker-hunt-state.json' in (ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
print('PASS v3.9.8 asset URL cache bust: 146 identical updated artwork images, 3 matching ARCore validations, data paths unchanged')
