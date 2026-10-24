from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import random,math,shutil
from pathlib import Path
root=Path('/mnt/data/hush_v3111')
art=root/'BrowserPreview/field_art_v73'
out=root/'BrowserPreview/themes_v74';out.mkdir(exist_ok=True)
W,H=720,1200
THEMES=[
('twilight-fox','other-fox.webp',(64,34,115),(14,20,48), (138,89,195), 21),
('blue-morpho-garden','butterfly-blue-morpho.webp',(20,80,83),(9,35,47),(37,174,173),44),
('mountain-deer','other-deer.webp',(85,120,162),(25,39,70),(218,177,112),76),
('robin-woodland','bird-robin.webp',(91,127,74),(15,49,46),(240,172,86),88),
('moonlit-owl','bird-owl.webp',(27,35,100),(7,19,41),(136,126,215),54),
('butterfly-meadow','butterfly-swallowtail.webp',(92,112,144),(23,65,54),(249,185,95),35),
]
for name,file,top,bottom,accent,seed in THEMES:
 rnd=random.Random(seed)
 im=Image.new('RGB',(W,H));pix=im.load()
 for y in range(H):
  t=y/H
  for x in range(W):
   d=(x/W-.5)**2
   light=math.exp(-((t-.37)/.34)**2)*.26
   tone=[int((top[i]*(1-t)**.65+bottom[i]*(1-(1-t)**.65))*(1-.46*d)+accent[i]*light) for i in range(3)]
   pix[x,y]=tuple(max(0,min(255,c)) for c in tone)
 overlay=Image.new('RGBA',(W,H),(0,0,0,0));dr=ImageDraw.Draw(overlay,'RGBA')
 # mountains / hills in middle third
 for layer in range(3):
  ybase=int(510+layer*125)
  points=[(-50,H)]
  for k in range(0,W+100,70):
   points.append((k,ybase+rnd.randint(-80,20)))
  points += [(W+50,H)]
  col=(18+layer*5,34+layer*6,44+layer*3, 55+layer*20)
  dr.polygon(points,fill=col)
 # natural trees from sides
 for side in [-1,1]:
  for i in range(12):
   y=rnd.randint(80,900);h=rnd.randint(125,335);x=rnd.randint(-45,215) if side==-1 else rnd.randint(505,760)
   width=rnd.randint(30,92);c=(12,36,39, 125) if y<500 else (10,32,25,150)
   dr.polygon([(x,y-h),(x-width,y),(x+width,y)],fill=c)
   dr.polygon([(x,y-h+55),(x-width*1.3,y+45),(x+width*1.3,y+45)],fill=c)
 # foreground leaves and floral speckles
 for i in range(290):
  x=rnd.randrange(W);y=rnd.randrange(H)
  if 170< x < 560 and 230<y<660:continue
  r=rnd.randint(2,13);alpha=rnd.randint(18,60)
  c=rnd.choice([(205,151,255),(150,213,210),(244,199,129),(225,140,184),(157,240,173)])
  dr.ellipse((x-r,y-r,x+r,y+r),fill=(*c,alpha))
 overlay=overlay.filter(ImageFilter.GaussianBlur(4))
 im=Image.alpha_composite(im.convert('RGBA'),overlay)
 cutout=root/'BrowserPreview/safari_cutouts_v63'/file.replace('.webp','.png')
 source=Image.open(cutout if cutout.exists() else art/file).convert('RGBA')
 # protect species labels? v73 art no text
 source=source.resize((545,545),Image.Resampling.LANCZOS)
 # animal artwork centered slightly above action buttons
 mask=source.getchannel('A').filter(ImageFilter.GaussianBlur(1))
 # tint/correct brightness a bit
 source=ImageEnhance.Contrast(source).enhance(1.06)
 source=ImageEnhance.Color(source).enhance(1.08)
 im.paste(source,(88,210),mask)
 # edges dark to preserve legibility
 shade=Image.new('RGBA',(W,H),(0,0,0,0));sh=ImageDraw.Draw(shade,'RGBA')
 for y in range(H):
  v=y/H
  a=int(100*(max(0,.22-v)/.22)**1.2 + 198*(max(0,v-.61)/.39)**1.3)
  if a: sh.line((0,y,W,y), fill=(4,10,24,max(0,min(230,a))))
 im=Image.alpha_composite(im,shade).convert('RGB')
 im.save(out/f'{name}.webp','WEBP',quality=87,method=5)
 print(name,(out/f'{name}.webp').stat().st_size)
raw=root/'WhiskerHunt/Resources/Raw/themes_v74'
shutil.copytree(out,raw,dirs_exist_ok=True)
# QA contact sheet
sheet=Image.new('RGB',(240*6,400),'#151922')
for i,(name,*_) in enumerate(THEMES):sheet.paste(Image.open(out/f'{name}.webp').resize((240,400)),(240*i,0))
sheet.save(root/'Theme_Preview_v74.jpg',quality=88)
