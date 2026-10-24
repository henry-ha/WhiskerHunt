"""Static source regression for screenshot's ARCore errors (not an Android compiler)."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
code=(ROOT/'WhiskerHunt/Platforms/Android/HushArCoreActivity.cs').read_text()
project=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
assert '<ApplicationDisplayVersion>3.9.0</ApplicationDisplayVersion>' in project
assert '<ApplicationVersion>54</ApplicationVersion>' in project
assert '<ApplicationId>uk.whiskerhunt.mobile</ApplicationId>' in project
assert 'using AndroidButton = Android.Widget.Button;' in code
assert 'using AndroidPaint = Android.Graphics.Paint;' in code
assert 'using AndroidRect = Android.Graphics.Rect;' in code
assert 'new AndroidButton(this)' in code and 'private AndroidButton?' in code
assert 'new AndroidRect(' in code and 'new AndroidPaint(' in code
assert re.search(r'\bSystem\.Environment\.TickCount64',code)
assert 'var eye = Multiply(_view, world);' in code
assert 'var clip = Multiply(_projection, eye);' in code
for forbidden in ['_surface.SetPreserveEGLContextOnPause(true)', 'new Button(', 'new Paint(', 'new Rect(', 'private Frame?', 'private Button?']:
 assert forbidden not in code, forbidden
native=ROOT/'WhiskerHunt/Resources/Raw';web=ROOT/'BrowserPreview'
for filename in ['app_v54.js', 'style_v54.css']:
 assert (web/filename).read_bytes()==(native/filename).read_bytes(),filename
assert 'window.whiskerNativeBridge=true;' in (native/'index_v54.html').read_text()
assert 'index_v54.html' in (ROOT/'WhiskerHunt/MainPage.xaml').read_text()
assert 'whisker-hunt-state.json' in (ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
assert 'app.GetString() != "Whisker Hunt"' in (ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
print('PASS ARCore source hotfix, Android/WebView version, resource parity and storage stability')
