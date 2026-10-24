from PIL import Image,ImageOps,ImageEnhance,ImageDraw,ImageFilter
from pathlib import Path
from math import sin,cos
import random,shutil
r=Path(__file__).resolve().parent.parent
p=r/'WhiskerHunt/Resources/Raw/field_art_v59';d=r/'BrowserPreview/field_art_v59'
N=3

def read(stem):return Image.open(p/(stem+'.webp')).convert('RGB').resize((240*N,240*N),Image.Resampling.LANCZOS)
def write(stem,img):
    img.resize((240,240),Image.Resampling.LANCZOS).save(p/(stem+'.webp'),'WEBP',quality=94,method=5)
def path(dd,points,color,width=2):dd.line([(round(x*N),round(y*N)) for x,y in points],fill=color,width=int(width*N),joint='curve')
def poly(dd,points,fill):dd.polygon([(round(x*N),round(y*N)) for x,y in points],fill=fill)
def circle(dd,x,y,rx,ry,c):dd.ellipse((round((x-rx)*N),round((y-ry)*N),round((x+rx)*N),round((y+ry)*N)),fill=c)

# Flying squirrels are flatter and spread a gliding membrane rather than upright bushy-tailed animals.
s=read('squirrel-flying-squirrel')
a=Image.new('RGBA',s.size);dr=ImageDraw.Draw(a)
poly(dr,[(34,112),(75,134),(127,160),(179,115),(182,151),(157,188),(84,198),(43,159)],(154,135,111,185))
for side in (-1,1):
    path(dr,[(124,158),(124+side*34,163),(124+side*81,142)],(92,80,65,230),3)
    for t in range(6):path(dr,[(121+side*(24+t*5),160+t*2),(119+side*(19+t*6),182+t)],(210,194,159,145),1)
s=Image.alpha_composite(s.convert('RGBA'),a).convert('RGB');write('squirrel-flying-squirrel',s)

# Other squirrel: clearly different orientation, pale cinnamon hue and pointed tail stripes.
s=ImageOps.mirror(read('squirrel-other-squirrel'))
s=ImageEnhance.Color(s).enhance(.75)
s=ImageEnhance.Brightness(s).enhance(1.05)
a=Image.new('RGBA',s.size);dr=ImageDraw.Draw(a)
for k in range(9):
    x=87+k*8
    path(dr,[(x,116+5*sin(k)),(x+8,142+4*sin(k))],(142,109,68,175),1.8)
s=Image.alpha_composite(s.convert('RGBA'),a).convert('RGB');write('squirrel-other-squirrel',s)

# Ground squirrel: tan colouring and earth-burrow setting, horizontal back stripes.
s=read('squirrel-ground-squirrel');s=ImageEnhance.Color(s).enhance(.62)
a=Image.new('RGBA',s.size);dr=ImageDraw.Draw(a)
for j in range(3): path(dr,[(94+j*9,140),(111+j*9,155),(130+j*10,160)],(88,57,30,187),3)
poly(dr,[(17,213),(222,212),(222,234),(17,235)],(117,87,49,122))
s=Image.alpha_composite(s.convert('RGBA'),a).convert('RGB');write('squirrel-ground-squirrel',s)

# Lionhead has a prominent light mane, lop retains drooping ears. The heads now face opposite sides.
s=ImageOps.mirror(read('rabbit-lionhead'))
a=Image.new('RGBA',s.size);dr=ImageDraw.Draw(a)
rng=random.Random(39)
for k in range(56):
    x=rng.uniform(55,191);y=rng.uniform(48,156)
    if 56<x<188 and 52<y<161:
        path(dr,[(x,y+9),(x+sin(k*.9)*8,y-7)],(233,195,142,rng.randint(94,156)),rng.uniform(.65,1.8))
s=Image.alpha_composite(s.convert('RGBA'),a).convert('RGB');write('rabbit-lionhead',s)

# Dwarf is a small compact bunny; Flemish giant fills its card with the large-bodied adult.
for stem,scale,bright in [('rabbit-netherland-dwarf',.86,1.12),('rabbit-flemish-giant',1.15,.94)]:
    s=read(stem);s=ImageEnhance.Brightness(s).enhance(bright)
    if scale<1:
        bg=s.getpixel((27*N,27*N));dst=Image.new('RGB',s.size,bg)
        shr=s.resize((int(s.width*scale),int(s.height*scale)),Image.Resampling.LANCZOS)
        dst.paste(shr,((s.width-shr.width)//2,(s.height-shr.height)//2));s=dst
    else:
        w=int(s.width/scale);h=int(s.height/scale)
        s=s.crop(((s.width-w)//2,(s.height-h)//2,(s.width+w)//2,(s.height+h)//2)).resize((240*N,240*N),Image.Resampling.LANCZOS)
    write(stem,s)

# Hedgehogs: long ears extra-visible, pygmy has distinctly light masked face, other is dark woodland variety.
s=ImageOps.mirror(read('hedgehog-african-pygmy-hedgehog'));s=ImageEnhance.Brightness(s).enhance(1.13);write('hedgehog-african-pygmy-hedgehog',s)
s=read('hedgehog-long-eared-hedgehog');a=Image.new('RGBA',s.size);dr=ImageDraw.Draw(a)
for x,y in [(99,92),(166,82)]:
    circle(dr,x,y,15,32,(174,125,100,217));circle(dr,x,y,9,23,(231,176,157,240))
s=Image.alpha_composite(s.convert('RGBA'),a).convert('RGB');write('hedgehog-long-eared-hedgehog',s)
s=read('hedgehog-other-hedgehog');s=ImageEnhance.Color(s).enhance(.65);s=ImageEnhance.Brightness(s).enhance(.86);write('hedgehog-other-hedgehog',s)

# Glass & amber are different snail species; shell tint + diagonal texture vs broad spiral band.
s=read('snail-amber-snail');a=Image.new('RGBA',s.size);dr=ImageDraw.Draw(a)
for k in range(10):
    x=51+k*11;y=102+3*sin(k*.6)
    path(dr,[(x,y),(x+17,142),(x+10,166)],(247,209,121,131),1.9)
s=Image.alpha_composite(s.convert('RGBA'),a).convert('RGB');write('snail-amber-snail',s)
s=read('snail-other-snail');s=ImageEnhance.Color(s).enhance(.68);s=ImageEnhance.Contrast(s).enhance(1.13);write('snail-other-snail',s)

for f in p.glob('*.webp'):shutil.copy2(f,d/f.name)
print('Refined squirrel, rabbit, hedgehog and shell silhouettes; synchronized Android/browser assets.')
