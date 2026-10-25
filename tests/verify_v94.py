"""Lightweight source/asset invariants for Hush Hunt v3.10.31.
Run from the package root: python tests/verify_v94.py
Native Android still requires a real .NET/ARCore device build.
"""
from pathlib import Path
import re
root = Path(__file__).resolve().parents[1]
app = root/'WhiskerHunt'
raw = app/'Resources/Raw'
checks = {
 'MAUI version': '3.10.31' in (app/'WhiskerHunt.csproj').read_text(),
 'Android build 94': '<ApplicationVersion>94</ApplicationVersion>' in (app/'WhiskerHunt.csproj').read_text(),
 'Package ID preserved': 'uk.whiskerhunt.mobile' in (app/'WhiskerHunt.csproj').read_text(),
 'Existing collection storage preserved': 'whisker-hunt-state.json' in (app/'MainPage.xaml.cs').read_text(),
 'WebView starts new entry': 'Source="index_v94.html"' in (app/'MainPage.xaml').read_text(),
 'Web JS versioned': 'src="app_v94.js"' in (raw/'index_v94.html').read_text(),
 'Web CSS versioned': 'href="style_v94.css"' in (raw/'index_v94.html').read_text(),
 '2D safe-label CSS present': '#encounter-ar-label' in (raw/'style_v94.css').read_text(),
 '2D position clamp': 'stageBounds.height-185' in (raw/'app_v94.js').read_text(),
 'AR model pinch resize': 'ResizeAnimal(distance / _previousPinchDistance)' in (app/'Platforms/Android/HushArCoreActivity.cs').read_text(),
 'AR model renders at user scale': '_host._animalSize' in (app/'Platforms/Android/HushArCoreActivity.cs').read_text(),
 'Model accepts size multiplier': 'float userScale=1f' in (app/'Platforms/Android/HushGlbAnimal3D.cs').read_text(),
 'Rear Camera2 retained': 'CameraCaptureSession' in (app/'Platforms/Android/HushWideCameraActivity.cs').read_text(),
 'Live camera non-white shutter': 'Rgb(245, 87, 117)' in (app/'Platforms/Android/HushWideCameraActivity.cs').read_text(),
 'AR capture PixelCopy retained': 'PixelCopy.Request' in (app/'Platforms/Android/HushArCoreActivity.cs').read_text(),
}
for n,ok in checks.items(): print(('PASS' if ok else 'FAIL')+'  '+n)
assert all(checks.values()),'One or more invariants failed'
