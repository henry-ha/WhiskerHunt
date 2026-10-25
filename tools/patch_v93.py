from pathlib import Path
r=Path(__file__).resolve().parents[1]/'WhiskerHunt'
a=r/'Platforms/Android/HushWideCameraActivity.cs'
s=a.read_text()
# Keep zoom buttons finger-sized while trimming wasteful grey overlay edges.
assert 'var item = new LinearLayout.LayoutParams(Dp(59), Dp(42));' in s
s=s.replace('var item = new LinearLayout.LayoutParams(Dp(59), Dp(42));','var item = new LinearLayout.LayoutParams(Dp(53), Dp(42));')
assert 'controls.AddView(zoomStrip);' in s
s=s.replace('controls.AddView(zoomStrip);','''// In a VERTICAL LinearLayout the default child width is MATCH_PARENT.
        // Explicit WRAP_CONTENT stops the grey zoom pill spanning the entire screen.
        var zoomParams = new LinearLayout.LayoutParams(-2, -2);
        zoomParams.Gravity = GravityFlags.CenterHorizontal;
        controls.AddView(zoomStrip, zoomParams);''')
assert 'new LinearLayout.LayoutParams(Dp(76), Dp(76))' in s
s=s.replace('new LinearLayout.LayoutParams(Dp(76), Dp(76))','new LinearLayout.LayoutParams(Dp(70), Dp(70))')
s=s.replace('shutterParams.TopMargin = Dp(8);','shutterParams.TopMargin = Dp(9);')
assert 'controlsParams.BottomMargin = Dp(94)' in s
s=s.replace('controlsParams.BottomMargin = Dp(94); // Raise entire camera controls above bottom system bar.', 'controlsParams.BottomMargin = Dp(112); // Extra safety gap: circular shutter and hint stay clear of Android navigation.')
a.write_text(s)
# Raise release code and entrypoint; do not alter app ID/data files.
proj=r/'WhiskerHunt.csproj';s=proj.read_text();assert '<ApplicationDisplayVersion>3.10.29</ApplicationDisplayVersion>' in s;s=s.replace('<ApplicationDisplayVersion>3.10.29</ApplicationDisplayVersion>','<ApplicationDisplayVersion>3.10.30</ApplicationDisplayVersion>').replace('<ApplicationVersion>92</ApplicationVersion>','<ApplicationVersion>93</ApplicationVersion>');proj.write_text(s)
page=r/'MainPage.xaml';s=page.read_text();assert 'index_v92.html' in s;page.write_text(s.replace('index_v92.html','index_v93.html'))
raw=r/'Resources/Raw'
ht=(raw/'index_v92.html').read_text().replace('3.10.29-92','3.10.30-93').replace('style_v92.css','style_v93.css').replace('app_v92.js','app_v93.js')
(raw/'index_v93.html').write_text(ht)
js=(raw/'app_v92.js').read_text()
assert "const WHISKER_BUILD='3.10.29', WHISKER_BUILD_NUMBER=92;" in js
js=js.replace("const WHISKER_BUILD='3.10.29', WHISKER_BUILD_NUMBER=92;", "const WHISKER_BUILD='3.10.30', WHISKER_BUILD_NUMBER=93;")
assert '<button data-ar-model="wildlife-ladybird-seven-spot" type="button">🐞 Seven-spot Ladybird</button>' in js
js=js.replace('''<p class="dim" style="margin:12px 0 4px">Available starter 3D animals (tap to choose):</p>''','''<p class="dim" style="margin:12px 0 4px"><strong>Choose a 3D animal</strong> (5 available). Tap a species to place it in your room:</p>''')
js=js.replace('''<button data-ar-model="wildlife-ladybird-seven-spot" type="button">🐞 Seven-spot Ladybird</button></div>''','''<button data-ar-model="wildlife-ladybird-seven-spot" type="button">🐞 Seven-spot Ladybird</button><button data-ar-model="wildlife-spider-garden-spider" type="button">🕷️ Garden Spider</button><button data-ar-model="wildlife-other-slug" type="button">🐌 Garden Slug</button></div>''')
assert "const HUSH_NATIVE_3D_STARTERS=['wildlife-snail-garden-snail','wildlife-snail-amber-snail','wildlife-ladybird-seven-spot'];" in js
js=js.replace("const HUSH_NATIVE_3D_STARTERS=['wildlife-snail-garden-snail','wildlife-snail-amber-snail','wildlife-ladybird-seven-spot'];", "const HUSH_NATIVE_3D_STARTERS=['wildlife-snail-garden-snail','wildlife-snail-amber-snail','wildlife-ladybird-seven-spot','wildlife-spider-garden-spider','wildlife-other-slug'];")
js=js.replace("const key=eligible.includes(selectedModelKey)?selectedModelKey:eligible[Math.floor(Math.random()*eligible.length)];", "const key=eligible.includes(selectedModelKey)?selectedModelKey:'wildlife-ladybird-seven-spot';")
js=js.replace('/* v3.10.29 build 92:','/* v3.10.30 build 93:').replace('/* v3.10.29:','/* v3.10.30:')
(raw/'app_v93.js').write_text(js)
(raw/'style_v93.css').write_bytes((raw/'style_v92.css').read_bytes())
sw=raw/'sw.js';js=sw.read_text();js=js.replace('index_v90.html','index_v93.html').replace('app_v90.js','app_v93.js').replace('style_v90.css','style_v93.css');sw.write_text(js)
print('source patched v3.10.30 build 93')
