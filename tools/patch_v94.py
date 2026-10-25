from pathlib import Path
r=Path(__file__).resolve().parents[1]/'WhiskerHunt'
raw=r/'Resources'/'Raw'
proj=r/'WhiskerHunt.csproj'
s=proj.read_text(encoding='utf-8')
assert '<ApplicationDisplayVersion>3.10.30</ApplicationDisplayVersion>' in s
proj.write_text(s.replace('<ApplicationDisplayVersion>3.10.30</ApplicationDisplayVersion>','<ApplicationDisplayVersion>3.10.31</ApplicationDisplayVersion>').replace('<ApplicationVersion>93</ApplicationVersion>','<ApplicationVersion>94</ApplicationVersion>'))
page=r/'MainPage.xaml';s=page.read_text();assert 'index_v93.html' in s;page.write_text(s.replace('index_v93.html','index_v94.html'))
h=(raw/'index_v93.html').read_text(encoding='utf-8').replace('3.10.30-93','3.10.31-94').replace('style_v93.css','style_v94.css').replace('app_v93.js','app_v94.js')
(raw/'index_v94.html').write_text(h,encoding='utf-8')
js=(raw/'app_v93.js').read_text(encoding='utf-8')
assert "const WHISKER_BUILD='3.10.30', WHISKER_BUILD_NUMBER=93;" in js
js=js.replace("const WHISKER_BUILD='3.10.30', WHISKER_BUILD_NUMBER=93;","const WHISKER_BUILD='3.10.31', WHISKER_BUILD_NUMBER=94;")
assert '<p class="dim" style="margin:12px 0 4px"><strong>Choose a 3D animal</strong> (5 available). Tap a species to place it in your room:</p>' in js
js=js.replace('<p class="dim" style="margin:12px 0 4px"><strong>Choose a 3D animal</strong> (5 available). Tap a species to place it in your room:</p>',
'''<p class="dim" style="margin:12px 0 4px"><strong>Choose a 3D animal</strong> (${HUSH_NATIVE_3D_STARTERS.length} installed). Select an animal to place it in your room. 2D Safari still includes the full wildlife collection.</p>''')
old='<div class="hush-ar-species-picks"><button data-ar-model="wildlife-snail-garden-snail" type="button">🐌 Garden Snail</button><button data-ar-model="wildlife-snail-amber-snail" type="button">🐌 Amber Snail</button><button data-ar-model="wildlife-ladybird-seven-spot" type="button">🐞 Seven-spot Ladybird</button><button data-ar-model="wildlife-spider-garden-spider" type="button">🕷️ Garden Spider</button><button data-ar-model="wildlife-other-slug" type="button">🐌 Garden Slug</button></div>'
assert old in js
js=js.replace(old,'<div class="hush-ar-species-picks">${HUSH_NATIVE_3D_BUTTONS}</div>')
old="const HUSH_NATIVE_3D_STARTERS=['wildlife-snail-garden-snail','wildlife-snail-amber-snail','wildlife-ladybird-seven-spot','wildlife-spider-garden-spider','wildlife-other-slug'];"
assert old in js
js=js.replace(old,'/* BEGIN GENERATED NATIVE 3D CHOICES (tools/import_cc0_wildlife.py) */\n'+old+'\nconst HUSH_NATIVE_3D_BUTTONS = \"\";\n/* END GENERATED NATIVE 3D CHOICES */')
# replace selectors with actual assets after model installer generates HUSH_NATIVE_3D_BUTTONS.
(raw/'app_v94.js').write_text(js,encoding='utf-8')
(raw/'style_v94.css').write_bytes((raw/'style_v93.css').read_bytes())
with (raw/'style_v94.css').open('a',encoding='utf-8') as f:
 f.write('''\n/* v3.10.31 - 3D species selector stays usable as the asset set grows */
.hush-ar-species-picks {max-height:40vh;overflow-y:auto;overscroll-behavior:contain;padding:4px 2px 12px;align-content:flex-start}
.hush-ar-species-picks button {text-align:center;white-space:normal;flex:1 0 125px;max-width:240px}
''')
sw=raw/'sw.js';s=sw.read_text();s=s.replace('index_v93.html','index_v94.html').replace('app_v93.js','app_v94.js').replace('style_v93.css','style_v94.css');sw.write_text(s)
# Improving silhouette proportion rather than turning dogs into 18 cm figures.
glb=r/'Platforms'/'Android'/'HushGlbAnimal3D.cs';s=glb.read_text()
old='float scale = group.Equals("snail", StringComparison.OrdinalIgnoreCase) ? .29f : .18f;'
assert old in s
new='''float scale = group.ToLowerInvariant() switch
            {
                "snail" => .22f, "ladybird" or "spider" or "bee" or "butterfly" or "ant" or "beetle" => .13f,
                "cat" => .47f, "dog" => .65f, "rabbit" => .35f, "bird" => .32f,
                "squirrel" => .31f, "hedgehog" => .24f, "frog" => .20f,
                "other" when variety.Equals("Deer", StringComparison.OrdinalIgnoreCase) => 1.05f,
                "other" when variety.Equals("Fox", StringComparison.OrdinalIgnoreCase) => .65f,
                "other" when variety.Equals("Tortoise", StringComparison.OrdinalIgnoreCase) => .35f,
                _ => .30f
            };'''
glb.write_text(s.replace(old,new))
print('v3.10.31 build 94 source patched')
