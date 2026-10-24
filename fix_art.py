from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import shutil
root=Path('/mnt/data/hush_v3111')
for base in [root/'BrowserPreview',root/'WhiskerHunt/Resources/Raw']:
 src=base/'field_art_v73'; dst=base/'field_art_v74'
 shutil.copytree(src,dst,dirs_exist_ok=True)
 for p in dst.glob('frog-*.webp'):
  im=Image.open(p).convert('RGB')
  clean=im.crop((0,0,im.width,int(im.height*.858))).resize(im.size,Image.Resampling.LANCZOS)
  clean.save(p,'WEBP',quality=91,method=6)
 # neutral symbolic OTHER artwork (no embedded text)
 S=256;im=Image.new('RGB',(S,S),'#183b4d')
 d=ImageDraw.Draw(im)
 for r,col in [(120,'#205768'),(87,'#286f69'),(60,'#3a9376')]:d.ellipse((128-r,128-r,128+r,128+r),fill=col)
 d.ellipse((91,79,162,150),outline='#e5faed',width=8)
 d.line((157,144,196,183),fill='#e5faed',width=13)
 d.ellipse((110,98,128,116),fill='#e5faed')
 d.line((119,115,119,130),fill='#e5faed',width=5)
 im.save(dst/'other-other.webp','WEBP',quality=93)
 # old not sure art retained only for old data, not displayed as new tile
 print(base,'frog art corrected',len(list(dst.glob('frog-*.webp'))))
