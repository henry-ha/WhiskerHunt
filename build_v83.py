from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import numpy as np, random, shutil, re, json
from pathlib import Path
root=Path('/mnt/data/hush_v3120_work')
files=sorted((root/'BrowserPreview/themes_v82').glob('*.webp'))
# The previous source art was a landscape panel padded with blurred extensions.
# Rebuild the panorama into a clean-edged, full-screen portrait: use only central art,
# extend background using crisp scenic geometry/gradients (never blur/gaussian repetition).
# This does NOT claim new detail in the old image; its output canvas is 2160x3840.
focus={'arctic-fox-snowfall':0,'autumn-hare':0,'butterfly-garden':0,'forest-owl':0,
       'golden-eagle-peaks':0,'highland-stag':0,'lakeside-swan':0,'meadow-rabbit':0,
       'moonlit-badger':0,'mountain-deer':0,'puffin-cliffs':0,'red-panda-bamboo':0,
       'red-squirrel-glade':0,'river-otter':0,'robin-dawn':0,'twilight-fox':0,
       'waterfall-kingfisher':0,'wildflower-bee-meadow':0,'woodland-frog':0,'woodland-hedgehog':0}

def lerp(a,b,t):return tuple(int(a[k]*(1-t)+b[k]*t) for k in range(3))
def dim(c,f):return tuple(max(0,min(255,int(x*f))) for x in c)
def create_one(p):
  src=Image.open(p).convert('RGB')
  scene=src.crop((0,550,1200,1210))
  # enhance the original clear scene without trying to invent texture via blur or interpolation
  scene=ImageEnhance.Contrast(scene).enhance(1.045)
  scene=scene.filter(ImageFilter.UnsharpMask(radius=1.0,percent=90,threshold=3))
  top=np.array(scene)[:45]; bot=np.array(scene)[-35:]
  topcol=tuple(np.median(top.reshape(-1,3),axis=0).astype('uint8').tolist());botcol=tuple(np.median(bot.reshape(-1,3),axis=0).astype('uint8').tolist())
  upper=dim(topcol,.37); lower=dim(botcol,.18)
  W,H=1200,2048
  ary=np.empty((H,W,3),dtype=np.uint8)
  # Clear painterly sky color grading, not the older photo blur or duplicate extension
  for y in range(H):
    if y<685:
      t=y/685;c=lerp(upper,topcol,min(1,t**.83))
    else:
      t=max(0,min(1,(y-1310)/(H-1310)));c=lerp(botcol,lower,t**.8)
    ary[y,:,:]=c
  base=Image.fromarray(ary,'RGB');d=ImageDraw.Draw(base,'RGBA')
  r=random.Random(p.stem)
  # fine-point atmospheric stars / floating pollen, not gaussian blur
  for i in range(115):
    x=r.randrange(10,W-10); y=r.randrange(10,760)
    radius=r.choice((1,1,1,2,3)); col=(255,242,210,r.randrange(16,65))
    d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=col)
  # mountains/forest at top to make the artwork extend naturally into the header area
  for depth, yy, alpha in [(1,595,36),(2,645,34)]:
    pts=[(-10,670)]; x=-10
    while x<W+80:
      pts.append((x,yy-r.randrange(0,70)+((x//170)%3)*19));x+=r.randrange(90,180)
    pts.extend([(W+10,690),(-10,690)])
    color=(*dim(topcol, .62 if depth==1 else .46),alpha)
    d.polygon(pts,fill=color)
  # bottom fine grass blades / wildflower stems, darkened naturally behind button labels
  for i in range(170):
    x=r.randrange(W); y=r.randrange(1640,2048)
    length=r.randrange(20,135); x2=x+r.randrange(-35,35)
    color=(*dim(botcol,.35+r.uniform(0,.22)),r.randrange(30,88))
    d.line([(x, min(H,y+length)),(x2,y)],fill=color,width=r.randrange(1,4))
  # Place the original clear wildlife composition across the full width.
  scene=scene.resize((W,800), Image.Resampling.LANCZOS)
  # Short soft-edged alpha only at the joins; no full-panel blurry image band
  alpha=Image.new('L',scene.size,255)
  arr=np.full((800,W),255,dtype=np.uint8)
  for k in range(64):
    # linear mask transition, no blurred source imagery
    a=int(255*(k+1)/64);arr[k,:]=a;arr[-k-1,:]=a
  alpha=Image.fromarray(arr)
  base.paste(scene,(0,620),alpha)
  # direct upscale for display pixel density; actual art detail is limited by original
  base=base.resize((2160,3840),Image.Resampling.LANCZOS)
  return base

for destroot in [root/'BrowserPreview',root/'WhiskerHunt/Resources/Raw']:
  out=destroot/'themes_v83';out.mkdir(exist_ok=True)
  thumbs=destroot/'theme_previews_v83';thumbs.mkdir(exist_ok=True)
  for p in files:
    target=out/(p.stem+'.webp')
    # regenerate only once in browser dir, copy bytes to Android assets
    if destroot.name=='Raw':
      shutil.copy2(root/'BrowserPreview/themes_v83'/target.name,target)
      shutil.copy2(root/'BrowserPreview/theme_previews_v83'/target.name, thumbs/target.name)
    else:
      pic=create_one(p)
      pic.save(target,'WEBP',quality=89,method=5)
      small=pic.resize((360,640),Image.Resampling.LANCZOS)
      small.save(thumbs/target.name,'WEBP',quality=88,method=5)
  # Main button scenes already contain an animal and no top/bottom wallpaper blur.
  # Preserve their original art but version the names so service workers cannot keep stale buttons.
  button=destroot/'button_scenes_v83';button.mkdir(exist_ok=True)
  for p in (destroot/'button_scenes_v82').glob('*.webp'):
    shutil.copy2(p,button/p.name)

# JS and CSS release entry points; skip all old versions, load new exact filenames.
for destroot in [root/'BrowserPreview',root/'WhiskerHunt/Resources/Raw']:
  app=(destroot/'app_v82.js').read_text()
  app=app.replace("const WHISKER_BUILD='3.10.19', WHISKER_BUILD_NUMBER=82;", "const WHISKER_BUILD='3.10.20', WHISKER_BUILD_NUMBER=83;",1)
  # modify only last theme array; old code is retained as legacy but not rendered.
  idx=app.index('const HUSH_THEMES_82=')
  app=app[:idx]+app[idx:].replace('themes_v82/','themes_v83/').replace('theme_previews_v82/','theme_previews_v83/').replace('button_scenes_v82/','button_scenes_v83/')
  app=app.replace('const HUSH_THEMES_82=', 'const HUSH_THEMES_83=')
  # Refs in new final implementation only; preserve older theme arrays (80) and saved user theme IDs.
  idx=app.index('const HUSH_THEMES_83=')
  app=app[:idx]+app[idx:].replace('HUSH_THEMES_82','HUSH_THEMES_83')
  # update versioned cache namespace and legacy v82 client test attributes
  idx=app.index('const HUSH_THEMES_83=')
  app=app[:idx]+app[idx:].replace('hush-v82-home','hush-v83-home').replace('data-hush-theme-system="v82"','data-hush-theme-system="v83"')
  app+= '\n/* v3.10.20: Home artwork uses full-frame, non-blurred v83 wallpapers. No legacy images are referenced by the active theme registry. */\n'
  (destroot/'app_v83.js').write_text(app)

  css=(destroot/'style_v82.css').read_text()
  css+='''
/* v3.10.20: remove every top/bottom blurred/vignetted artwork band. */
.hush-story-hero.hush-immersive-home.hush-v83-home {
  background: #111b2e !important;
  isolation: isolate !important;
  overflow: hidden !important;
}
.hush-story-hero.hush-immersive-home.hush-v83-home::before,
.hush-story-hero.hush-immersive-home.hush-v83-home::after {
  content:none !important;display:none !important;background:none !important;
  filter:none !important;backdrop-filter:none !important;
}
.hush-story-hero.hush-immersive-home.hush-v83-home>.hush-theme-photo {
  position:absolute !important;inset:0 !important;
  width:100% !important;height:100% !important;
  object-fit:cover !important;object-position:center center !important;
  filter:none !important;opacity:1 !important;
  display:block !important;pointer-events:none !important;z-index:0 !important;
  transform:none !important;
}
.hush-v83-home .hush-story-brand,.hush-v83-home .hush-story-topbar,
.hush-v83-home .hush-home-action-zone,.hush-v83-home .hush-home-hero-spacer {
  z-index:2 !important;position:relative !important;
}
.hush-v83-home .hush-story-main>.hush-scene-card-art {
  object-fit:cover !important;object-position:50% 45% !important;
  filter:none !important;opacity:1 !important;
}
.hush-v83-home .hush-story-main::before {
  background:linear-gradient(180deg,rgba(0,10,25,0) 15%, rgba(0,10,25,.75) 100%) !important;
}
/* Keep readable labels without any horizontal blur strip. */
.hush-v83-home .hush-story-brand h1,.hush-v83-home .hush-story-brand p,
.hush-v83-home .hush-story-main strong,.hush-v83-home .hush-story-main small {
 text-shadow:0 2px 5px rgba(2,13,28,.9),0 1px 2px rgba(0,0,0,.8) !important;
}
'''
  (destroot/'style_v83.css').write_text(css)
  for index in ['index.html','index_v82.html']:
    f=destroot/index
    text=f.read_text().replace('app_v82.js','app_v83.js').replace('style_v82.css','style_v83.css').replace('3.10.19-82','3.10.20-83')
    f.write_text(text)
  (destroot/'index_v83.html').write_text((destroot/'index.html').read_text())
  sw=(destroot/'sw.js').read_text().replace('whisker-hunt-shell-v82','whisker-hunt-shell-v83').replace('index_v82.html','index_v83.html').replace('app_v82.js','app_v83.js').replace('style_v82.css','style_v83.css')
  (destroot/'sw.js').write_text(sw)

proj=root/'WhiskerHunt/WhiskerHunt.csproj'
text=proj.read_text().replace('<ApplicationDisplayVersion>3.10.19</ApplicationDisplayVersion>','<ApplicationDisplayVersion>3.10.20</ApplicationDisplayVersion>').replace('<ApplicationVersion>82</ApplicationVersion>','<ApplicationVersion>83</ApplicationVersion>')
proj.write_text(text)
page=root/'WhiskerHunt/MainPage.xaml'
page.write_text(page.read_text().replace('index_v82.html','index_v83.html'))

(root/'CHANGELOG_v3.10.20.md').write_text('''# Hush Hunt v3.10.20 · build 83

- Rebuilt all 20 active Home wallpapers using the original central wildlife compositions, without the previous **top and bottom blurred photo extensions**.
- Added scene-themed sharp atmospheric sky/foreground render layers; removed active Home CSS vignette overlay and gaussian/backdrop blurs from the theme background.
- Updated each active theme path to new `themes_v83` images, plus matching `theme_previews_v83` to avoid stale UI previews.
- Kept existing button artwork and re-versioned it to `button_scenes_v83` to invalidate stale caches.
- Preserved saved theme IDs, Dynamic/Static behavior, collection storage and the app package ID.
- Updated `MainPage.xaml` and WebView source entry points to v83 assets, and Android version to v3.10.20 (83).

**Important image-quality note:** Files have a 2160×3840 raster canvas with crisp generated overlay scenery, but central subjects were reconstructed from previously small artwork. This is not the same as newly rendered native-detail 4K animal illustration. Original source resolution limits fine details; a real 4K remaster of all 20 would require new original high-detail imagery.
''')
print('generated', len(files), 'new wallpapers; new version 83')
