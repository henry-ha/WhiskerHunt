"""Hush Hunt v3.9.5 offline wildlife icon refinement.
Keeps the existing user-approved icons where appropriate, adds species-specific anatomy and markings.
Self-contained PIL processing. All output remains 240x240 WEBP in both MAUI and browser assets.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from math import sin,cos,pi
import random, shutil
ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'WhiskerHunt/Resources/Raw/field_art_v59'
DST=ROOT/'BrowserPreview/field_art_v59'
S=3

def point(x,y): return (int(x*S),int(y*S))
def box(x0,y0,x1,y1): return (*point(x0,y0),*point(x1,y1))
def line(d, xy, fill, width=2, joint='curve'):
    d.line([point(*p) for p in xy],fill=fill,width=round(width*S),joint=joint)
def ellipse(d, xy, fill, outline=None,width=1): d.ellipse(box(*xy),fill,outline,width=round(width*S))
def polygon(d,xy,fill,outline=None,width=1): d.polygon([point(*p) for p in xy],fill);(line(d,xy+[xy[0]],outline,width) if outline else None)
def arc(d,xy,start,end,fill,width):d.arc(box(*xy),start,end,fill,round(width*S))
def draw_variant(stem,callback, colorize=None):
    f=SRC/f'{stem}.webp'
    if not f.exists(): print('MISSING',f);return
    img=Image.open(f).convert('RGBA').resize((240*S,240*S),Image.Resampling.LANCZOS)
    if colorize: img=ImageEnhance.Color(img).enhance(colorize)
    layer=Image.new('RGBA',img.size);d=ImageDraw.Draw(layer)
    callback(d,layer)
    img=Image.alpha_composite(img,layer).convert('RGB')
    img=img.resize((240,240),Image.Resampling.LANCZOS)
    img.save(f,format='WEBP',quality=91,method=5)
    return f



def cat_detail(name):
    def fn(d,layer):
        # Add more natural fur markings, muzzle shading and breed-like cues while keeping the cute card style.
        rng=random.Random('cat:'+name)
        for i in range(26):
            x=78+rng.random()*86; y=78+rng.random()*98
            line(d,[(x,y),(x+rng.uniform(-3,3),y+rng.uniform(6,11))],'#ffffff33',1)
        if 'tabby' in name or 'ginger' in name or 'grey' in name:
            for x in (95,108,121,134,147):
                line(d,[(x,73),(x-4,92),(x-1,112)],'#6a563e88',2)
        if 'calico' in name or 'tortoiseshell' in name:
            for x,y,c in ((96,90,'#b36a34aa'),(143,119,'#433a36aa'),(118,154,'#e3c19799')):
                ellipse(d,(x-16,y-12,x+16,y+12),c)
        if 'tuxedo' in name:
            polygon(d,[(107,145),(121,171),(136,145)],'#f7f5f0cc')
        if 'colourpoint' in name:
            ellipse(d,(76,77,109,124),'#6d564dcc'); ellipse(d,(136,78,169,124),'#6d564dcc'); ellipse(d,(103,126,139,154),'#7a6458bb')
        # whiskers
        for y in (143,149,155):
            line(d,[(85,y),(63,y-3)],'#eadfd4aa',1)
            line(d,[(157,y),(179,y-3)],'#eadfd4aa',1)
    return fn


def dog_detail(name):
    def fn(d,layer):
        # Fur texture and breed-specific cues for the requested dog kinds.
        rng=random.Random('dog:'+name)
        if name=='golden-retriever':
            for x in range(72,170,8):
                line(d,[(x,150),(x+rng.uniform(-2,2),173+rng.uniform(-3,4))],'#f7e6be99',2)
            ellipse(d,(84,145,156,182),'#f5e4c099')
        elif name=='poodle':
            for x,y,r in ((74,78,16),(94,66,15),(122,62,15),(148,76,16),(82,146,13),(154,147,13)):
                ellipse(d,(x-r,y-r,x+r,y+r),'#f6ead6a0','#ead7be66',1)
        elif name=='terrier':
            for x in range(77,162,7):
                line(d,[(x,92+rng.randint(-5,5)),(x+rng.randint(-4,4),84+rng.randint(-11,-3))],'#f2e3bf88',1)
            line(d,[(69,130),(51,154)],'#b48758aa',3)
            line(d,[(170,129),(188,152)],'#b48758aa',3)
        elif name=='spaniel':
            # restore a cleaner two-ear spaniel with feathered ear fur
            for side in (-1,1):
                x=120+side*52
                for i in range(8):
                    line(d,[(x,y:=92+i*7),(x+side*rng.randint(4,12),y+10)],'#9a6846aa',2)
        elif name=='bulldog':
            ellipse(d,(95,136,145,166),'#fff3de88')
            line(d,[(101,122),(95,134),(100,149)],'#7c645a99',2)
            line(d,[(140,122),(146,134),(142,149)],'#7c645a99',2)
            line(d,[(110,155),(130,155)],'#56453f88',2)
        elif name=='dachshund':
            line(d,[(60,169),(184,168)],'#8b5d3faa',2)
            for x in (86,154): line(d,[(x,184),(x-3,199)],'#8b5d3faa',2)
        elif name=='husky':
            polygon(d,[(84,89),(119,72),(157,90),(145,136),(119,122),(95,138)],'#fbfbf7d2')
            line(d,[(99,74),(88,54)],'#edece6aa',2)
            line(d,[(140,74),(151,53)],'#edece6aa',2)
        elif name=='mixed-breed':
            # make the mixed breed clearly dog-like with one semi-erect ear and one floppy ear, patchy coat
            ellipse(d,(92,148,149,184),'#f7e7cb88')
            ellipse(d,(86,91,118,121),'#f2d8b0aa')
            ellipse(d,(136,91,168,122),'#b9794eaa')
            for x,y,c in ((94,109,'#b97a49bb'),(135,125,'#ffffff88'),(145,150,'#9c6b49aa')):
                ellipse(d,(x-14,y-10,x+14,y+10),c)
            line(d,[(73,131),(61,152)],'#a96d48aa',3)
            line(d,[(167,132),(183,150)],'#a96d48aa',3)
    return fn

def detail_snail(label):
    colors={'garden-snail':('#784c2c','#be9a62'), 'grove-snail':('#8d754d','#f0d29d'),
            'roman-snail':('#654d3d','#e7d0a1'), 'amber-snail':('#ba7530','#efc87a'),
            'other-snail':('#4d6541','#b2a471'), 'glass-snail':('#b7b9ab','#e0e3d0'), 'pond-snail':('#5d4e37','#9d9b7c')}
    dark,bright=colors[label]
    def draw(d,layer):
        if label in ('garden-snail','grove-snail'):
            # Highlight shell ridges, stripes and whorls in the same illustrative detail as the naturalist cards.
            for i in range(13):
                x=80+i*4
                y=117+9*sin(i*.57)
                line(d,[(x,y),(x-1,y+21),(x-4,y+36)],dark+'88',.8)
            for r in [12,19,26,34]:arc(d,(94-r,133-r,94+r,133+r),50,300,dark+'aa',1.5)
            for j in range(40):
                x=60+j*2.1;y=184+2*sin(j*.5)
                ellipse(d,(x,y,x+1.5,y+1.1),'#74523d66')
        elif label=='roman-snail':
            # Large Roman shell: pale shell rim and broad irregular ochre bands.
            for i in range(11):
                x=55+i*8;y=109+9*sin(i*.72)
                line(d,[(x,y),(x-3,y+16),(x-4,y+34)],('#a97538' if i%2 else '#ffdb97')+'bb',2)
            arc(d,(30,77,175,215),196,352,'#f8e7bfcc',2)
        elif label=='amber-snail':
            # Small transparent amber shell, diagonal glossy highlights (not Roman's heavy stripes).
            ellipse(d,(38,85,176,204),'#e89e4e26')
            for i in range(12):line(d,[(53+i*7,131+i%3*2),(84+i*6,86+i%3*3)],'#fae5ac44',1.6)
            arc(d,(70,91,145,162),40,297,'#fff5c9bb',3)
        elif label=='other-snail':
            # Brown/green mottled woodland specimen, distinct from amber or Roman.
            for i in range(30):
                x=60+(i*41%102);y=101+(i*37%67)
                ellipse(d,(x,y,x+5,y+3),('#486b3a77' if i%2 else '#d0c28b99'))
            for r in (15,26,36):arc(d,(110-r,133-r,110+r,133+r),60,325,'#544c3799',1.2)
        elif label=='glass-snail':
            for r in (16,27,36): arc(d,(108-r,134-r,108+r,134+r),25,325,'#ffffe6bb',1.1)
        elif label=='pond-snail':
            for y in range(175,205,6):line(d,[(45,y),(191,y+1)],'#83bb9d66',1)
    return draw

def butterfly_details(name,kind):
    def fn(d,layer):
        rng=random.Random('flutter:'+name)
        m=name.replace('-', ' ')
        # Wing vein tracery and distinct eyespots/stripes for each named variety.
        for side in (-1,1):
            base=119
            for n in range(4):
                start=(base+side*(7+n*2),125+n*6)
                end=(base+side*(48+n*3),82+n*11)
                line(d,[start,(base+side*(27+n*5),96+n*6),end],('#64473c91' if kind=='butterfly' else '#6652599d'),.9)
            for n in range(3):line(d,[(120+side*5,139),(120+side*(40+n*6),151+n*10)],'#684b5685',.85)
        if 'peacock' in m or 'emperor' in m:
            for x,y in [(72,111),(168,111),(81,161),(159,161)]:
                ellipse(d,(x-10,y-9,x+10,y+9),'#323d66bb')
                ellipse(d,(x-5,y-4,x+5,y+4),'#a3d4df')
        if 'admiral' in m:
            for side in (-1,1):line(d,[(120+side*12,106),(120+side*64,96)],'#ed7858dc',8)
        if 'small tortoiseshell' in m or 'painted lady' in m:
            for x in (65,81,95,143,161,176):ellipse(d,(x-2,113,x+3,118),'#fff4c5')
        if 'common blue' in m:
            for side in (-1,1):
                for i in range(4):ellipse(d,(120+side*(22+11*i)-2,150+6*i,120+side*(22+11*i)+2,154+6*i),'#d7f8e6dd')
        if 'brimstone' in m:line(d,[(93,96),(77,126),(62,143)],'#e5ad4aca',1.5)
        if kind=='moth':
            # Moth markings and feathery antennae instead of butterfly-like rods.
            for side in (-1,1):
                for i in range(5):
                    x=120+side*(24+i*12);y=108+(i%2)*22
                    ellipse(d,(x-3,y-3,x+3,y+3),'#f9e3cd88')
                for n in range(5):line(d,[(120+side*4,94+n*2),(120+side*(11+n*2),90+n*2)],'#573d4488',1)
            if 'tiger' in m or 'burnet' in m:
                for i in range(5):
                    x=60+(i*33%121);y=100+(i*14%51)
                    ellipse(d,(x-7,y-5,x+6,y+4),'#422d4099')
            if 'silver y' in m:line(d,[(151,127),(164,138),(151,144)],'#f5ecdccc',2)
    return fn

def bee_detail(name):
    def fn(d,layer):
        for i in range(54):
            rng=random.Random(i*31+len(name)*47)
            x=74+rng.random()*101;y=119+rng.random()*59
            if (x-125)**2/58**2+(y-144)**2/32**2<=1.0:
                line(d,[(x,y),(x+1.5*rng.random(),y-3-rng.random()*5)],'#f6e5a699',.8)
        for side in (-1,1):
            for y in (97,105,112):line(d,[(125+side*12,y+15),(125+side*(29+int(y/20)),y-16)],'#ffffff77',1)
        if 'leafcutter' in name:
            polygon(d,[(180,173),(207,163),(197,187),(177,194)],'#73a870ad','#497f60',1)
        elif 'carder' in name:
            for i in range(18):
                x=89+(i*17%72);y=116+(i*13%54)
                ellipse(d,(x,y,x+5,y+3),'#c2895fa2')
        elif 'mining' in name:
            for x in (72,80,88):line(d,[(x,159),(x-11,165)],'#79563f99',1)
        elif 'white-tailed' in name:ellipse(d,(157,128,190,168),'#f9f7eecc')
        elif 'red-tailed' in name:ellipse(d,(157,127,190,169),'#a84f39bb')
        elif 'buff-tailed' in name:ellipse(d,(158,131,191,169),'#ddcd9cbb')
    return fn

def beetle_ladybird(name,kind):
    def fn(d,layer):
        rng=random.Random(name)
        if kind=='ladybird':
            # Species-specific spotted elytra; highlights give a more polished shell.
            count={'two-spot':2,'seven-spot':7,'fourteen-spot':14,'twenty-two-spot':22,'pine-ladybird':4,'harlequin':12}.get(name,7)
            for i in range(count):
                x=68+(i*37%109);y=100+(i*43%74)
                if ((x-124)/56)**2+((y-144)/47)**2<.78:
                    r=4.2 if count<=7 else 2.7
                    ellipse(d,(x-r,y-r,x+r,y+r),'#2c2c39cc')
            arc(d,(68,96,179,188),190,293,'#fffdf1c9',2.5)
        else:
            # Elytra, legs and specialized features instead of uniform beetle silhouettes.
            for i in range(8):
                x=87+i*10; y=121+int(5*sin(i))
                line(d,[(x,y),(x+10,y+47)],'#efe8cf6d',1)
            line(d,[(123,113),(123,180)],'#382c3299',2)
            if 'stag' in name:
                for side in (-1,1):
                    line(d,[(112+side*9,99),(109+side*29,70),(105+side*23,82)],'#4a3027',3)
            if 'longhorn' in name:
                for side in (-1,1):line(d,[(123+side*9,109),(123+side*69,52),(123+side*86,75)],'#54493c',2)
            if 'rose' in name:
                for i in range(17):
                    x=88+(i*19%78);y=119+(i*37%53)
                    ellipse(d,(x-2,y-2,x+3,y+3),'#c7f4a55e')
    return fn

def spider_detail(name):
    def fn(d,layer):
        if name in ('wolf-spider','crab-spider','cellar-spider'): return
        for i in range(15):
            x=105+(i*13%51);y=118+(i*37%48)
            ellipse(d,(x-2,y-2,x+2,y+2), '#ead4af9a' if i%2 else '#634d3e99')
        for side in (-1,1):
            for k in range(4):
                x=120+side*(12+k*4);y=137+k*7
                line(d,[(x,y),(x+side*(30+k*3),y-28+k*7),(x+side*(46+k*4),y+4+k*8)],'#87705caa',1)
        if 'zebra' in name:
            for k in range(4):line(d,[(111+k*9,111),(106+k*9,152)],'#f0f0e1e5',3)
        if 'garden' in name:
            for off in (-16,0,16):ellipse(d,(117+off,130,122+off,135),'#e8d7b9')
        if 'jumping' in name:
            for x in (78,95):
                ellipse(d,(x-9,133,x+9,149),'#2d2a32')
                ellipse(d,(x-4,136,x+1,142),'#eee9df')
    return fn

def bird_detail(name):
    def fn(d,layer):
        # Detailed feather strokes: species-specific wing, bib, beak, breast and tail marks.
        if name in ('owl','swan'):return
        if 'blackbird' in name:
            beak='#d8a239';wing='#2c302d';breast='#363a34'
        elif 'blue-tit' in name:
            beak='#554934';wing='#3d7bc5';breast='#f8df6b'
        elif 'great-tit' in name:
            beak='#554934';wing='#78966e';breast='#f2d35d'
        elif 'robin' in name:
            beak='#5b4833';wing='#746b4b';breast='#b35231'
        elif 'magpie' in name:
            beak='#777477';wing='#1e2933';breast='#eeede4'
        elif 'crow' in name:
            beak='#464347';wing='#3d4042';breast='#34383a'
        elif 'wood-pigeon' in name:
            beak='#b97962';wing='#8d95a0';breast='#b8a0a0'
        elif 'starling' in name:
            beak='#f5d26b';wing='#4c4247';breast='#4e4449'
        elif 'seagull' in name:
            beak='#ddb360';wing='#a5b4bd';breast='#f2f3ef'
        elif 'parakeet' in name:
            beak='#be8876';wing='#469e69';breast='#6ac486'
        elif 'duck' in name:
            beak='#d8a14a';wing='#806046';breast='#d5af70'
        else:
            beak='#b78f62';wing='#7c6045';breast='#e4c7a2'
        for i in range(8):
            x=146+i*4;y=144+(i%3)*3
            line(d,[(x,y),(x+12,y+17)],wing+'bc',1.5)
        # breast feather detailing
        for i in range(8):
            x=103+(i*13%55);y=151+(i*21%27)
            line(d,[(x,y),(x+3,y+6)],breast+'b0',1.1)
        if name=='starling':
            for i in range(23):
                x=104+(i*17%79);y=121+(i*33%62)
                ellipse(d,(x,y,x+2.8,y+2.8),'#f4ead8da')
        if name=='house-sparrow':
            polygon(d,[(92,107),(119,112),(118,124),(95,131)],'#643c33a9')
        if name in ('great-tit','blue-tit'):
            line(d,[(105,112),(121,129),(125,167)],'#273b44',4)
            line(d,[(90,108),(114,110)],'#29363a',2.5)
        if name=='robin':
            ellipse(d,(88,116,131,151),'#c76d3ba0')
        if name=='magpie':
            polygon(d,[(176,159),(229,189),(209,174),(193,177)],'#3c3547','#d4d5de',1.1)
        if name=='parakeet':
            line(d,[(168,175),(206,218),(201,228)],'#348b6c',4)
        if name=='duck':
            polygon(d,[(67,139),(39,148),(67,153)],'#deb05b')
        if name=='wood-pigeon':
            line(d,[(100,117),(115,120)],'#f2f1e3',3)
        if name=='seagull':
            line(d,[(165,148),(193,151)],'#636872',2)
    return fn

def frog_detail(name):
    def fn(d,layer):
        if name=='tree-frog':return
        rng=random.Random(name)
        tint={'common-frog':'#5a5437','pool-frog':'#40694f','marsh-frog':'#678c35','bullfrog':'#3a4936','other-frog':'#8e7457'}.get(name,'#637548')
        for i in range(24):
            x=69+rng.random()*106;y=113+rng.random()*64
            if ((x-121)/58)**2+((y-148)/42)**2<=.97:
                rr=rng.uniform(2.5,7)
                ellipse(d,(x-rr,y-rr,x+rr,y+rr),tint+'9c')
        # more believable long fingers and hind legs
        for side in (-1,1):
            x=120+side*49
            line(d,[(x,170),(x+side*22,187),(x+side*34,178)],'#527a4fd5',3)
            for n in range(3):ellipse(d,(x+side*(27+n*5)-2,176+n%2*4,x+side*(27+n*5)+4,184+n%2*4),'#b0d18ca6')
        if name=='bullfrog':
            ellipse(d,(82,154,155,194),'#6d855888')
            line(d,[(100,121),(144,121)],'#46604aba',2)
            ellipse(d,(76,129,96,147),'#60725288'); ellipse(d,(145,129,165,147),'#60725288')
        if name=='common-frog':
            for side in (-1,1):line(d,[(120+side*24,114),(120+side*39,139)],'#564d3ba8',4)
            ellipse(d,(92,160,149,191),'#6e5b4740')
        if name=='pool-frog':
            line(d,[(120,121),(120,186)],'#d1d481a6',3)
            for y in range(125,180,12): ellipse(d,(116,y,124,y+5),'#f2f2b488')
        if name=='marsh-frog':
            for x in (88,111,138,163):ellipse(d,(x,150,x+7,155),'#516b3ea8')
            ellipse(d,(78,120,165,185),'#88a73a22')
    return fn

def photo_distinct(name,group):
    def fn(d,layer):
        if group=='rabbit':
            if name=='lionhead':
                for k in range(33):
                    x=65+(k*21%128);y=50+(k*31%62)
                    line(d,[(x,y+17),(x+3*sin(k),y+3)],'#d7ac7799',2.2)
            if name=='lop-eared':
                # Ears droop naturally around cheeks (base art already floppy).
                for s in (-1,1):
                    x=120+s*59
                    arc(d,(x-18,90,x+20,185),30 if s>0 else 145,180 if s>0 else 330,'#927d6b9c',2)
            if name=='netherland-dwarf':
                ellipse(d,(88,132,160,198),'#ffffff12')
                for s in (-1,1):ellipse(d,(120+s*32-3,171,120+s*32+3,179),'#eddbba98')
                ellipse(d,(79,86,94,132),'#f2c2cf55'); ellipse(d,(104,86,119,132),'#f2c2cf55')
            if name=='flemish-giant':
                ellipse(d,(61,144,185,206),'#00000008')
                for k in range(13):
                    x=45+(k*13%138);y=159+(k*11%51)
                    line(d,[(x,y),(x+5,y+8)],'#846a5695',1.2)
                line(d,[(72,69),(76,120)],'#8f7862aa',2)
                line(d,[(109,69),(113,120)],'#8f7862aa',2)
        elif group=='squirrel':
            if name=='flying-squirrel':
                # Visible gliding membrane and contrasting leading edge.
                polygon(d,[(74,120),(34,185),(86,196),(161,170),(173,113)],'#cbbba099','#6d6c6699',2)
                line(d,[(47,177),(95,170),(154,154)],'#f8f2e0c8',2)
            if name=='ground-squirrel':
                for j in range(5):
                    x=99+j*9
                    line(d,[(x,165),(x+7,184)],'#8d5c3eb0',2)
                polygon(d,[(30,210),(205,210),(192,219),(37,219)],'#ad98676f')
            if name=='other-squirrel':
                for j in range(7):
                    x=130+j*7;y=100+j*5
                    line(d,[(x,y),(x+14,y-5)],'#e3d6adbb',2)
        elif group=='hedgehog':
            if name=='long-eared-hedgehog':
                for x in (89,151):
                    ellipse(d,(x-12,61,x+12,109),'#ba8a7188','#e8b8a3a3',1)
            if name=='other-hedgehog':
                for k in range(23):
                    x=47+(k*19%146);y=64+(k*31%67)
                    line(d,[(x,y+11),(x-3,y-2)],'#b18d6c99',1.3)
            if name=='african-pygmy-hedgehog':
                for k in range(16):
                    x=69+(k*17%114);y=81+(k*27%60)
                    line(d,[(x,y),(x+3,y+5)],'#ebe1cc7f',1.2)
    return fn

changed=[]
def apply(stem,fn,col=None):
    if draw_variant(stem,fn,col):changed.append(stem)

for f in SRC.glob('cat-*.webp'):
    if f.stem.endswith('-group'):continue
    apply(f.stem,cat_detail(f.stem[4:]))
for f in SRC.glob('dog-*.webp'):
    if f.stem.endswith('-group'):continue
    apply(f.stem,dog_detail(f.stem[4:]))
for g in ['garden-snail','grove-snail','roman-snail','glass-snail','amber-snail','pond-snail','other-snail']:
    apply('snail-'+g,detail_snail(g))
for group in ('butterfly','moth'):
    for f in SRC.glob(group+'-*.webp'):
        if f.stem.endswith('-group'):continue
        apply(f.stem,butterfly_details(f.stem[len(group)+1:],group))
for f in SRC.glob('bee-*.webp'):
    if f.stem.endswith('-group'):continue
    apply(f.stem,bee_detail(f.stem[4:]))
for group in ('ladybird','beetle'):
    for f in SRC.glob(group+'-*.webp'):
        if f.stem.endswith('-group'):continue
        apply(f.stem,beetle_ladybird(f.stem[len(group)+1:],group))
for f in SRC.glob('spider-*.webp'):
    if f.stem.endswith('-group'):continue
    apply(f.stem,spider_detail(f.stem[7:]))
for f in SRC.glob('bird-*.webp'):
    if f.stem.endswith('-group'):continue
    apply(f.stem,bird_detail(f.stem[5:]))
for f in SRC.glob('frog-*.webp'):
    if f.stem.endswith('-group'):continue
    apply(f.stem,frog_detail(f.stem[5:]))
for group in ['rabbit','squirrel','hedgehog']:
    for f in SRC.glob(group+'-*.webp'):
        if f.stem.endswith('-group'):continue
        apply(f.stem,photo_distinct(f.stem[len(group)+1:],group))

# Better distinction for Garden vs Grove shell art through individual warm/cool grading and relief.
# Restore the previously approved, simpler but clearer Spaniel with only TWO floppy ears.
oldspan=ROOT/'dog_spaniel_older.webp'
if oldspan.exists():
    im=Image.open(oldspan).convert('RGB').resize((240,240),Image.Resampling.LANCZOS)
    im.save(SRC/'dog-spaniel.webp','WEBP',quality=95)
    changed.append('dog-spaniel')
# Existing detailed main dog icon uses a generic Labrador face rather than shaggy breed-specific body.
main=SRC/'dog-group.webp'
if main.exists():
    dog=Image.open(SRC/'dog-labrador.webp').convert('RGB').resize((240,240),Image.Resampling.LANCZOS)
    dog.save(main,'WEBP',quality=92)
    changed.append('dog-group')
# Crop safety: no full-bleed touches, pad the animals that previously looked cut off.
for key in ('other-slug','other-worm','other-fish','other-tortoise','other-animal'):
    f=SRC/(key+'.webp')
    if not f.exists():continue
    im=Image.open(f).convert('RGB')
    bg=im.getpixel((20,20))
    padded=Image.new('RGB',(240,240),bg)
    shrunk=im.resize((216,216),Image.Resampling.LANCZOS)
    padded.paste(shrunk,(12,12))
    padded.save(f,'WEBP',quality=92)
    changed.append(key)
for f in SRC.glob('*.webp'):
    shutil.copy2(f,DST/f.name)
print('REFINED',len(changed),'icons:',', '.join(changed))
(ROOT/'HushHunt_v3.9.5_ARTWORK_FILES.txt').write_text('\n'.join(changed)+'\n')
