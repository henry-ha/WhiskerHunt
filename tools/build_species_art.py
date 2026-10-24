"""Offline, original illustrated species variants for Hush Hunt.
Variety-specific colours, silhouettes, markings and morphology, not numbered copies.
Run: python3 tools/build_species_art.py
Approved concept-sheet animals are integrated for the exact matched varieties.
"""
from pathlib import Path
import re, json, io, hashlib, math, random
import cairosvg
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFilter
ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT/'BrowserPreview/app.js').read_text()
raw = re.search(r'const FIELD_GUIDE_VARIETIES=(\{.*?\});', JS).group(1)
TYPES = json.loads(raw)
TARGETS=[ROOT/'BrowserPreview/field_art',ROOT/'WhiskerHunt/Resources/Raw/field_art']
poster=Path(__file__).with_name('approved_variant_poster.png')

def slug(t): return re.sub(r'^-|-$','',re.sub(r'[^a-z0-9]+','-',t.lower()))
def E(x,y,rx,ry,fill,stroke='#593f3c',sw=2,extra=''):
 return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'
def C(x,y,r,fill,stroke='#593f3c',sw=2): return E(x,y,r,r,fill,stroke,sw)
def P(d,fill='none',stroke='#65474b',sw=3,extra=''): return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
def R(x,y,w,h,rx,fill,stroke='#65474b',sw=2):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def polygon(pts,fill,stroke='#65474b',sw=2):return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>'

def draw(species, typ, i):
 seed=int.from_bytes(hashlib.blake2b((species+'|'+typ).encode(),digest_size=4).digest(),'big')
 rnd=random.Random(seed)
 pal=['#9ccdef','#adddb3','#efd1b0','#d0b3e8','#f4bfcf','#f0dc9f','#b5dfd2','#baccec']
 bg=pal[i%len(pal)]
 cream='#fff4de';stroke='#62504d';dark='#382c35'
 paint = {
 'Cat':['#e9ad48','#e89b2e','#a6754f','#292d37','#f6f3e9','#f7deaa','#262c34','#e8aa6c','#60462f','#9ea5ae','#eee3d2','#e4ad64'],
 'Dog':['#efd4a0','#e5ad55','#e2d1bd','#9a6c4d','#e2b579','#c58a4c','#ae6945','#aab3bc','#cdbb91'],
 'Snail':['#b97b44','#dfbf78','#b7a38e','#f1a95b','#f4c477','#8eae9c','#e0a569'],
 'Dragonfly':['#36ad82','#62aee2','#356dc4','#db6543','#dfad40','#2b272a'],
 'Spider':['#765a49','#8c756a','#704f3d','#decbb8','#5b534d','#eacb6b','#bda180'],
 'Bird':['#dc7449','#342c31','#8d735a','#6baedb','#d6cf77','#333c51','#ab9c8e','#714643','#44434d','#fbf5ef','#5ac574','#e5c06d','#f8fbf9','#8a6a4b'],
 'Bee':['#e7b735','#f5c359','#ba493e','#f2d35a','#d39e57','#e1aa35','#c8a050'],
 'Moth':['#a58a69','#dc9a9a','#97b27a','#deb98b','#e4ca67','#d1a4bd','#bec4bc'],
 'Butterfly':['#8c4059','#c6454d','#da8245','#e1a25f','#b18645','#eee6c7','#587eb8','#e8d658'],
 'Ladybird':['#d33938','#e76342','#ba553b','#f0cf55','#2c3a34','#ece7cc'],
 'Beetle':['#543c38','#4f9e72','#514b3d','#3b4851','#a67b45','#294b43','#52593f','#704c39'],
 'Ant':['#3c3536','#ad4b3f','#ab4d27','#d6ac4e','#4f3c33','#5a4c42'],
 'Squirrel':['#9c9c9c','#c3733a','#bfa487','#af9367','#9d9e8f'],
 'Rabbit':['#bcad90','#bd9b7a','#f2f0eb','#a57451','#f2e2d2','#cfb394'],
 'Hedgehog':['#9a6f50','#956a51','#d5a27b','#ae8f75'],
 'Frog':['#72a264','#78a58e','#7dbe6a','#b0db68','#756c49','#a4ae82'],
 'Other':['#c77e52','#b6a582','#928a78','#67545e','#889b66','#b3a69a','#82a1d2','#6baec7','#b6b38a','#9cb0ae']
 }
 color=paint.get(species,['#e4bb8e'])[i%len(paint.get(species,[1]))]
 strong=paint.get(species,[color])[(i+2)%len(paint.get(species,[1]))]
 light='#fff1db'; eye=lambda x,y: C(x,y,5.5,'#29313b','none',0)+C(x-2,y-2,1.8,'white','none',0)
 parts=[]
 # playful illustrated backdrop; varies by group and category
 parts += [f'<rect width="240" height="240" rx="28" fill="{bg}"/>',C(120,115,95,cream,'none',0),C(42,41,7,'#ffffffb0','none',0),C(199,38,4,'white','none',0)]
 # Small ground accent
 if species not in {'Butterfly','Moth','Dragonfly','Bee','Bird'}:
  parts += [P('M27 196 Q120 212 215 196','#e2cfaa','none',0),P('M35 199 Q40 175 54 168 Q50 183 49 199','#79b17c','none',0),P('M204 198 Q201 179 189 170 Q190 188 192 200','#79b17c','none',0)]
 # family shapes
 if species=='Cat':
  parts += [E(122,177,47,38,color),P('M158 176 Q203 125 199 187','none',color,18)]
  parts += [polygon('63,83 76,31 111,68',color),polygon('130,67 170,31 181,88',color),polygon('76,74 82,49 100,78','#efb0a8','none',0),polygon('146,73 166,50 166,82','#efb0a8','none',0)]
  parts += [E(123,117,65,53,color),E(99,169,15,13,color),E(146,169,15,13,color)]
  m=typ.lower()
  if any(k in m for k in ('black','tuxedo','colourpoint')):
   parts += [P('M67 107 Q65 64 98 77 Q112 98 102 128 Z','#2e343d','none',0)]
  if 'white' in m: parts += [E(122,127,48,40,'#f9f9f4')]
  if 'tuxedo' in m: parts += [P('M107 146 L123 164 L139 145','#faf5ed','none',0)]
  if 'calico' in m: parts += [E(105,86,20,21,'#f5f3eb','none',0), E(144,124,21,18,'#303640','none',0)]
  if 'tortoiseshell' in m: parts += [E(97,104,20,12,'#4e3733','none',0),E(149,124,23,15,'#c47f3f','none',0),E(142,81,11,12,'#4e3733','none',0)]
  if 'tabby' in m or 'ginger' in m or 'grey' in m:
   for j in range(3):parts += [P(f'M{107+j*13} 70 l4 16','none',strong,5)]
  if 'colourpoint' in m: parts += [E(121,128,17,14,'#714f49','none',0),E(80,77,18,25,'#714f49','none',0),E(158,77,18,25,'#714f49','none',0)]
  parts += [eye(102,118),eye(144,118),polygon('118,136 126,136 122,143','#b46e72','none',0),P('M122 142 q-8 10 -16 2 M122 142 q8 10 16 2','none',dark,2)]
  for yy in (143,148):parts += [P(f'M88 {yy} L63 {yy-4} M156 {yy} L181 {yy-4}','none','#786864',1.5)]
 elif species=='Dog':
  m=typ.lower(); long='dachshund' in m; erect=('husky' in m or 'terrier' in m); short='bulldog' in m
  parts += [E(121,169,68 if long else 50,31 if short else 37,color),E(91,195,13,10,color),E(154,195,13,10,color),P('M169 174 Q202 150 195 125','none',color,16)]
  if erect:
   parts += [polygon('64,92 65,42 100,74',color),polygon('140,69 173,40 167,96',color)]
  else:
   parts += [E(67,109,21,38,strong),E(166,110,21,39,strong)]
  parts += [E(118,115,48 if short else 53,45,color)]
  if 'poodle' in m:
   for x,y in ((75,80),(94,64),(123,60),(150,78),(83,141),(154,143)):
    parts += [C(x,y,17,color,'none',0)]
  if 'husky' in m:parts += [P('M82 88 Q118 66 155 91 L145 135 Q120 117 97 138 Z','#fbfbfb','none',0)]
  if 'terrier' in m:parts += [E(121,160,25,15,'#f8e4bf','none',0)]
  if 'spaniel' in m:parts += [E(69,123,19,43,strong),E(172,125,19,43,strong)]
  if 'golden' in m:parts += [E(116,152,26,21,light,'none',0)]
  parts += [eye(99,119),eye(140,119),E(119,145,18,12,light,'none',0),C(119,140,6,dark,'none',0),P('M119 146 q-11 10 -17 0 M119 146 q11 10 17 0','none',dark,2)]
  if i%2==0:parts += [P('M119 149 Q119 170 127 164 Q135 157 119 149','#f389a3','none',0)]
 elif species=='Snail':
  m=typ.lower(); pond='pond' in m; amber='amber' in m; glass='glass' in m; roman='roman' in m; grove='grove' in m; garden='garden' in m; other_snail='other' in m
  body='#efba79' if not pond else '#b6d8b1'
  shell=('#8a5733' if garden else '#d8c08c' if grove else '#8f857b' if roman else '#d9caa8' if glass else '#e1b55c' if amber else '#91b5a6' if pond else color)
  parts += [P('M48 198 Q120 208 196 196','#dcc9a2','none',0),P('M46 198 Q56 175 71 165 Q66 184 64 198','#79b17c','none',0),P('M192 197 Q189 177 176 168 Q177 186 179 198','#79b17c','none',0)]
  parts += [E(150,171,63,29,body,'#d49b68',2),E(158,156,54,24,body,'#d49b68',2),P('M199 169 Q212 127 206 103','none','#eab87c',13),P('M177 165 Q177 112 178 92','none','#eab87c',10)]
  parts += [C(170,91,6,'#efb67f'),C(205,98,6,'#efb67f'),C(170,90,2.8,dark,'none',0),C(205,97,2.8,dark,'none',0),P('M182 132 q9 8 18 -1','none',dark,2)]
  r=(50 if roman else 39 if glass or amber else 47)
  parts += [C(106,137,r,shell,'#82644b',4)]
  spiral_color='#6e4b38' if not pond else '#6f7d73'
  parts += [P('M110 136 C129 107 140 153 111 156 C86 161 92 121 110 120 C124 122 129 145 110 140','none',spiral_color,4)]
  if garden or grove:
   for offset in (-18,-2,14): parts += [P(f'M{100+offset} 99 q10 23 -2 57','none','#76543e',3.4)]
  if amber:
   parts += [E(106,137,r-6,r-8,'#efcf74aa','none',0),P('M84 122 q21 -14 44 -12','none','#b38038',2)]
  if glass:
   parts += [C(106,137,r,'#dfe5dfaa','none',0),P('M78 138 q29 -24 57 0','none','#b6bbb6',2)]
  if roman:
   parts += [P('M71 136 q34 -27 70 3','none','#7a675f',2.8),P('M86 105 q15 -10 28 -6','none','#7a675f',2)]
  if pond:
   parts += [E(106,137,r,'#8db6ac','#5d7f74',3),P('M64 161 q24 18 81 12','none','#7cc1a8',3),P('M62 184 q35 10 79 1','none','#7cc1a8',3)]
  if other_snail:
   parts += [P('M84 108 q23 -17 46 0','none','#a06d53',2.8),P('M83 149 q26 12 48 -2','none','#a06d53',2.4)]
 elif species in {'Butterfly','Moth'}:
  moth=species=='Moth'; m=typ.lower()
  upper=48 if moth else 56; lower=40 if moth else 46
  upper_fill=color; lower_fill=strong
  if 'large white' in m or 'white' in m and species=='Butterfly': upper_fill='#fbf6e8'; lower_fill='#f0e473'
  if 'common blue' in m: upper_fill='#6c8fd5'; lower_fill='#8c285b'
  if 'brimstone' in m: upper_fill='#efe467'; lower_fill='#e3524e'
  if 'painted lady' in m: upper_fill='#df9853'; lower_fill='#f4ebcf'
  if 'small tortoiseshell' in m: upper_fill='#df8d49'; lower_fill='#b8904b'
  if 'red admiral' in m: upper_fill='#d94c45'; lower_fill='#e6a05e'
  if 'peacock' in m: upper_fill='#914767'; lower_fill='#e08a43'
  for side in (-1,1):
   ux=120+side*31; lx=120+side*27
   parts += [P(f'M120 118 Q{ux+side*34} 62 {ux+side*upper} 84 Q{ux+side*59} 132 120 138Z',upper_fill,'#5d4960',3)]
   parts += [P(f'M120 126 Q{lx+side*34} 116 {lx+side*lower} 163 Q{lx+side*12} 191 120 141Z',lower_fill,'#5d4960',2.6)]
   parts += [P(f'M120 120 Q{ux+side*20} 94 {ux+side*40} 88','none','#f8f1d6',2),P(f'M120 128 Q{lx+side*22} 136 {lx+side*36} 160','none','#f7efd8',2)]
   for sx,sy in ((ux+side*12,102),(ux+side*28,118),(lx+side*18,146)):
    parts += [C(sx,sy,4,'#fff8cd','none',0)]
   if any(k in m for k in ('admiral','peacock','painted')):
    parts += [E(ux+side*12,114,11,10,'#243447','none',0),C(ux+side*12,114,5,'#74bbe0','none',0)]
   if 'peacock' in m:
    parts += [E(lx+side*19,150,10,8,'#233649','none',0),C(lx+side*19,150,4,'#8fd4f0','none',0)]
   if 'white' in m:
    parts += [E(ux+side*18,114,12,24,'#faf7ea','none',0)]
   if 'comma' in m:
    parts += [P(f'M{ux+side*24} 107 q{side*12} -8 {side*17} 3','none','#efdab6',3)]
  parts += [E(120,136,8,39,'#6b564c'),C(120,97,12,'#73564b'),P('M116 90 Q95 58 103 53 M124 90 Q145 58 138 53','none',dark,3),eye(116,95),eye(124,95)]
  if moth:
   parts += [E(120,151,15,22,'#d8c7a0bb','none',0)]
 elif species=='Dragonfly':
  m=typ.lower(); abdomen=('#2b88b9' if 'emperor' in m else '#73a6d5' if 'broad' in m else '#2f2f2f' if 'hawker' in m else '#cf5238' if 'darter' in m else '#d39a33' if 'four' in m else '#23282c')
  thorax=('#6fcf4d' if 'emperor' in m else '#63463c' if 'broad' in m else '#a9d44d' if 'hawker' in m else '#e26c41' if 'darter' in m else '#f0c44c' if 'four' in m else '#2f2f2a')
  parts += [P('M120 113 Q101 83 66 76 Q36 76 35 97 Q79 124 120 119Z','#d9f3ffb4','#7eb6ce',2),P('M120 120 Q77 110 47 140 Q35 165 65 165 Q98 160 120 130Z','#d9f3ff98','#7eb6ce',2),P('M120 113 Q139 83 174 76 Q204 76 205 97 Q161 124 120 119Z','#d9f3ffb4','#7eb6ce',2),P('M120 120 Q163 110 193 140 Q205 165 175 165 Q142 160 120 130Z','#d9f3ff98','#7eb6ce',2)]
  for side in (-1,1):
   for wy in (93,145):
    parts += [P(f'M120 {118 if wy==93 else 126} Q{120+side*28} {wy} {120+side*74} {wy+6}','none','#b7dcec',1.6)]
  if 'darter' in m:
   for side in (-1,1): parts += [E(152 if side>0 else 88,131,8,5,'#ec6154','none',0)]
  if 'four' in m:
   for x,y in ((88,106),(152,106),(79,145),(161,145)): parts += [E(x,y,6,5,'#5b4d41','none',0)]
  if 'golden' in m:
   parts += [P('M111 126 Q109 153 110 206','none','#2b2b24',4),P('M130 126 Q132 153 131 206','none','#2b2b24',4)]
   for yy in (149,166,183,200): parts += [P(f'M110 {yy} L131 {yy}','none','#d4ae4d',3)]
  else:
   parts += [P('M120 124 Q108 156 108 206 Q123 229 132 205 Q134 159 121 125 Z',abdomen,'#2d637a',2)]
   for yy in (158,172,186,200):parts += [P(f'M108 {yy} Q120 {yy+5} 133 {yy}','none','#345875',2)]
  parts += [E(120,120,18,28,thorax),C(104,99,19,thorax),C(135,99,19,thorax),C(103,99,11,'#22505c','none',0),C(135,99,11,'#22505c','none',0),C(104,95,3,'#ffffff','none',0),C(137,95,3,'#ffffff','none',0)]
  if 'hawker' in m:
   for yy in (155,170,185,200): parts += [P(f'M110 {yy} L130 {yy}','none','#d9d051',3)]
  for side in (-1,1):
   parts += [P(f'M{120+side*10} 137 l{side*32} 20 m{-side*21} -5 l{side*24} 26','none','#4f777f',3)]
 elif species=='Ant':
  parts += [C(82,140,24,color),C(121,145,13,strong),E(165,149,36+(i%3)*3,29,color)]
  for side in (-1,1):
   for x in (114,139,164):parts += [P(f'M{x} 154 Q{x+side*16} 178 {x+side*35} 193','none','#564644',4)]
  parts += [P('M73 121 q-9 -20 -23 -24 M92 118 q6 -22 20 -21','none','#594941',3),eye(74,141),eye(92,143)]
  if i%2==1:parts += [P('M154 132 l8 12 8 -12 m-8 12 l8 12 8 -10','none',strong,4)]
 elif species=='Spider':
  m=typ.lower(); long='cellar' in m; crab='crab' in m; jumping='jumping' in m; zebra='zebra' in m; garden='garden' in m; house='house' in m
  abdomen=18 if jumping or zebra else 30 if long else 36 if crab else 42
  parts += [E(128,142,abdomen,33 if not (jumping or zebra) else 20,color),C(92,150,18,strong)]
  for side in (-1,1):
   for n in range(4):
    x=120+side*(n*8-8); reach=(100 if long else 68 if crab else 52 if jumping else 58)
    y=126+n*13
    sw=2.5 if long else 5 if not (jumping or zebra) else 4
    parts += [P(f'M{x} {y} Q{x+side*reach*.45} {y-42+n*9} {x+side*reach} {y-41+n*22}','none',stroke,sw)]
  if garden:
   parts += [P('M128 110 l-8 23 16 0Z','#f7edc7','none',0),E(128,146,15,12,'#a88957','none',0)]
  elif house:
   parts += [E(128,135,17,13,'#8e755b','none',0),P('M112 121 q17 -10 30 0','none','#6c584a',3)]
  elif jumping:
   parts += [E(128,136,15,13,'#6d5746','none',0),C(83,146,7,'#1f2731','none',0),C(101,147,7,'#1f2731','none',0),C(85,144,2,'white','none',0),C(103,145,2,'white','none',0)]
  elif zebra:
   parts += [E(128,136,16,13,'#e7dfd0','none',0)]
   for xx in (114,126,138): parts += [R(xx,116,6,50,2,'#4c4741','none',0)]
  elif crab:
   parts += [E(128,139,14,12,strong,'none',0)]
  parts += [eye(85,148),eye(99,149),C(92,158,2,'#67454c','none',0)]
 elif species=='Bird':
  m=typ.lower();duck='duck' in m or 'swan' in m; owl='owl' in m; parrot='parakeet' in m
  parts += [E(128,158,47 if not duck else 63,41,color),P('M159 169 Q191 153 200 179 L164 180',strong,'none',0),C(104,117,31,color)]
  if owl:
   parts += [polygon('84,99 76,66 105,92',color),polygon('113,92 145,68 140,113',color)]
   parts += [C(94,116,14,light,'none',0),C(117,116,14,light,'none',0)]
  parts += [E(148,166,29,20,strong,'none',0),eye(96,114)]
  if owl:parts += [eye(118,114)]
  parts += [polygon('77,125 55,132 80,139','#df994b','none',0)]
  for x in (116,146):parts += [P(f'M{x} 190 l-5 13 m5 -13 l6 13','none','#aa754a',3)]
  if 'robin' in m:parts += [E(107,164,21,24,'#db703b','none',0)]
  if 'magpie' in m:parts += [P('M152 170 L211 179 L174 163','#282f3a','none',0),E(147,163,20,16,'#f8f7f2','none',0)]
  if 'blue' in m:parts += [P('M83 101 Q93 76 117 94','none','#3373a2',9)]
  if parrot:parts += [P('M169 176 Q202 209 186 228','none','#52ad80',11)]
 elif species=='Bee':
  m=typ.lower(); tail='white' if 'white-tailed' in m else 'red' if 'red-tailed' in m else 'buff' if 'buff-tailed' in m else 'carder' if 'carder' in m else 'leaf' if 'leafcutter' in m else 'mining' if 'mining' in m else 'honey'
  parts += [E(101,109,33,22,'#c6eff7aa','#75b9cb',2,extra='transform="rotate(-30 101 109)"'),E(151,109,33,22,'#c6eff7aa','#75b9cb',2,extra='transform="rotate(30 151 109)"')]
  thorax='#d5a156' if tail in ('honey','carder','leaf') else '#1d1b1b' if tail in ('white','red','buff') else '#b17a57'
  abdomen='#efc24d' if tail!='red' else '#d35e45'
  parts += [E(126,146,57,37,abdomen),C(89,143,22,thorax),E(126,146,60,39,'none','#60493d',2)]
  stripe_cols=['#3c312e','#3c312e','#3c312e']
  for xx in (108,134,158): parts += [R(xx,114,12,64,5,stripe_cols[(xx//10)%3],'none',0)]
  if tail=='white': parts += [E(160,147,14,16,'#fbf6e8','none',0)]
  if tail=='red': parts += [E(160,147,14,16,'#c44539','none',0)]
  if tail=='buff': parts += [E(160,147,14,16,'#e8d0a0','none',0)]
  if tail=='leaf': parts += [P('M147 177 q18 8 29 -2','none','#6ea75c',4)]
  if tail=='mining': parts += [P('M84 174 q12 9 24 0','none','#b98050',4)]
  if 'bumblebee' in m: parts += [E(128,171,38,15,light+'aa','none',0)]
  parts += [eye(82,140),P('M75 125 q-10 -19 -20 -20 M89 120 q3 -20 17 -20','none','#48403f',3),P('M104 128 q18 -10 42 0','none','#5b473d',2)]
 elif species=='Ladybird':
  spots=2 if 'two' in typ.lower() else 14 if 'fourteen' in typ.lower() else 22 if 'twenty' in typ.lower() else 7
  parts += [C(116,145,55,color),P('M116 95 L116 200','none','#2c3333',4),C(113,95,23,'#333d3e')]
  for n in range(min(spots,12)):
   theta=2*math.pi*(n+.5)/min(spots,12)
   xx=116+34*math.cos(theta);yy=145+32*math.sin(theta)
   parts += [C(round(xx,1),round(yy,1),4 if spots>7 else 8,'#2d3333','none',0)]
  parts += [eye(104,91),eye(124,91)]
 elif species=='Beetle':
  m=typ.lower()
  parts += [E(120,153,49,55,color),P('M120 97 V206','none',strong,3),C(120,99,24,strong)]
  if 'stag' in m:parts += [P('M105 86 Q80 63 85 45 M135 86 Q160 63 154 45','none','#5c4539',8)]
  for side in (-1,1):
   for yy in (128,151,174):parts += [P(f'M{120+side*28} {yy} q{side*30} 1 {side*40} 30','none','#66534c',5)]
  if i%3==0:parts += [E(102,148,8,15,'#d9d1aa','none',0),E(144,145,8,15,'#d9d1aa','none',0)]
  parts += [eye(111,99),eye(133,99)]
 elif species=='Squirrel':
  m=typ.lower(); flying='flying' in m; ground='ground' in m; red='red' in m; grey='grey' in m
  tail_col=strong if not red else '#b9713e'
  parts += [P('M158 179 Q210 178 207 103 Q205 42 160 68 Q199 78 188 129 Q183 160 151 151Z',tail_col,'#795a43',4)]
  if flying:
   parts += [P('M91 141 Q121 165 150 145 Q147 174 118 182 Q92 176 82 159Z','#efe1bf','#8d7b67',2)]
  parts += [E(121,170,46,36,color),C(97,114,34,color),polygon('73,94 79,58 103,87',color),polygon('109,90 134,58 130,102',color),E(125,176,23,23,light,'none',0),E(88,167,15,9,color),E(153,163,12,8,color)]
  if red: parts += [P('M78 62 l8 10 m26 -10 l-8 10','none','#7b4e2d',3)]
  if ground: parts += [P('M77 193 q22 15 46 6','none','#8c735b',4)]
  if grey: parts += [P('M160 82 q22 18 22 54','none','#c8c5bd',4)]
  parts += [eye(90,112),C(114,130,5,'#8c5552','none',0),P('M112 132 q-6 8 -14 3','none','#6d4a49',2)]
 elif species=='Rabbit':
  m=typ.lower(); lop='lop' in m; lion='lionhead' in m; dwarf='dwarf' in m; giant='giant' in m; dutch='dutch' in m
  body_w=60 if giant else 50 if dwarf else 54
  parts += [E(137,173,body_w,36,color),C(94,116,38,color),E(160,181,24,20,light,'none',0),C(180,171,13,'#f2dfcd','none',0),E(100,176,14,10,color)]
  if lop:
   parts += [E(65,88,13,46,strong,extra='transform="rotate(-32 65 88)"'),E(130,89,13,46,strong,extra='transform="rotate(30 130 89)"')]
  else:
   parts += [E(78,62,13,57,color,extra='transform="rotate(-7 78 62)"'),E(113,61,13,58,color,extra='transform="rotate(9 113 61)"'),E(78,59,6,38,'#e8a9b5','none',0),E(113,58,6,39,'#e8a9b5','none',0)]
  if lion: parts += [E(96,116,46,42,'#d4a87d','none',0)]
  if dutch: parts += [P('M73 103 Q90 88 114 101 L117 143 Q95 132 74 144 Z','#f8f6f2','none',0)]
  parts += [eye(84,117),C(109,136,4,'#a67f7c','none',0),P('M109 140 q-6 7 -13 2 M109 140 q6 7 12 2','none','#8d6965',2)]
 elif species=='Hedgehog':
  m=typ.lower(); long='long-eared' in m; african='african' in m
  parts += [E(132,155,66,48,color),E(116,161,47,37,light,'none',0)]
  for j in range(18):
   xx=72+j*7; yy=122-(j%4)*4
   parts += [polygon(f'{xx},{yy+10} {xx-8},{yy-14} {xx+12},{yy+7}',strong,'none',0)]
  if long:
   parts += [E(92,111,12,21,'#d6a98d'),E(118,107,11,20,'#d6a98d')]
  elif african:
   parts += [E(95,112,10,16,'#c98f6d'),E(117,109,9,15,'#c98f6d')]
  else:
   parts += [E(93,114,9,13,'#b78667'),E(115,112,9,12,'#b78667')]
  parts += [P('M157 168 q15 0 22 6','none','#88614f',3),eye(98,153),eye(127,154),C(142,173,5,'#775653','none',0),C(90,191,10,color),C(157,191,10,color)]
 elif species=='Frog':
  parts += [E(117,159,59,41,color),C(91,114,19,color),C(146,114,19,color),C(91,113,10,'#f8f8e1','none',0),C(146,113,10,'#f8f8e1','none',0),eye(91,113),eye(146,113),P('M96 157 Q121 175 147 155','none','#457b48',3)]
  parts += [P('M73 179 Q46 187 49 211 M161 179 Q190 187 188 211','none',color,14)]
  if 'tree' in typ.lower():parts += [C(48,211,11,'#df7448'),C(188,211,11,'#df7448')]
 elif species=='Other':
  m=typ.lower()
  if 'fish' in m:
   parts += [E(114,149,59,31,color),polygon('171,147 210,115 209,181',strong),polygon('82,148 66,137 66,160','#86c7df','none',0),C(87,143,7,'#263846','none',0),P('M108 136 q24 9 36 0','none','#dceef7',2)]
  elif 'worm' in m:
   parts += [P('M52 178 Q67 111 114 150 T189 143','none','#b8a692',31),C(185,139,6,dark,'none',0)]
  elif 'slug' in m:
   parts += [P('M49 180 Q69 134 114 150 T193 151','none','#8ea8d4',31),C(184,145,6,dark,'none',0),P('M176 141 l14 -9 m-14 9 l13 10','none','#8ea8d4',5)]
  elif 'bat' in m:
   parts += [P('M119 132 Q82 66 24 113 Q58 105 59 159 Q84 123 119 149 Q154 123 180 159 Q181 105 215 113 Q158 66 119 132',color),C(119,122,24,strong),eye(109,123),eye(130,123)]
  elif 'lizard' in m:
   parts += [E(118,157,56,22,color),P('M156 164 Q204 167 210 124','none',color,11),C(73,149,20,strong),P('M95 167 l-24 18 m35 -11 l-28 24','none','#6f8b58',4),eye(67,145)]
  elif 'tortoise' in m:
   parts += [E(119,153,60,41,strong),E(118,157,44,29,color,'none',0),C(181,159,17,color),eye(183,155),P('M87 154 q29 -16 59 0','none','#796450',3)]
  elif 'fox' in m:
   parts += [P('M153 176 Q199 132 188 102 Q183 79 160 72 Q176 94 171 129 Q166 161 144 166Z',strong,'#81573f',4),E(121,171,47,34,color),C(98,114,35,color),polygon('72,97 79,58 104,88',color),polygon('107,89 134,59 130,103',color),E(126,175,22,22,light,'none',0),eye(90,113),C(114,130,5,'#2f2929','none',0)]
  elif 'deer' in m:
   parts += [E(121,171,48,35,color),C(98,114,34,color),polygon('73,96 80,64 101,89',color),polygon('108,90 132,63 129,103',color),P('M80 67 q-12 -18 -19 -26 m26 16 q-10 -20 -9 -28 M111 65 q9 -18 20 -26 m-24 18 q12 -20 12 -28','none','#8d735a',3),E(126,176,20,20,light,'none',0),eye(91,114)]
  elif 'mouse' in m:
   parts += [P('M154 173 Q196 182 205 151','none','#8e8478',6),E(121,172,49,33,color),C(99,115,32,color),C(83,91,17,'#cbb3b0'),C(116,91,17,'#cbb3b0'),eye(90,115),C(114,132,4,'#6e5354','none',0)]
  else:
   parts += [E(122,172,54,34,color),C(101,118,37,color),polygon('72,102 78,62 97,86',color),polygon('114,88 146,62 137,114',color),E(128,173,21,22,light,'none',0),eye(91,116),C(116,133,5,dark,'none',0)]
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 240 240">'+''.join(parts)+'</svg>'

def generate():
 for d in TARGETS:d.mkdir(parents=True,exist_ok=True)
 n=0
 for group,types in TYPES.items():
  for i,typ in enumerate(types):
   svg=draw(group,typ,i)
   png=cairosvg.svg2png(bytestring=svg.encode(),output_width=480,output_height=480)
   img=Image.open(io.BytesIO(png)).convert('RGB').resize((240,240),Image.Resampling.LANCZOS)
   dest=f'{slug(group)}-{slug(typ)}.webp'
   for d in TARGETS:img.save(d/dest,'WEBP',quality=91,method=4)
   n+=1
  svg=draw(group,types[0],0)
  png=cairosvg.svg2png(bytestring=svg.encode(),output_width=480,output_height=480)
  img=Image.open(io.BytesIO(png)).convert('RGB').resize((240,240),Image.Resampling.LANCZOS)
  for d in TARGETS: img.save(d/(slug(group)+'-group.webp'),'WEBP',quality=91,method=4)
 print('Generated',n,'bespoke subtype illustrations for',len(TYPES),'groups')
 return n

# Crop the user-approved artwork concept where it includes the exact matching subtype.
# Cropping retains the creature's real differences in anatomical features and patterning.
APPROVED_POSTER={
 'Cat': {'Tabby':(42,215,190,365),'Calico':(216,215,367,365),'Tuxedo':(395,215,545,365),'Tortoiseshell':(574,215,725,365),'Colourpoint':(750,215,900,365)},
 'Dog': {'Labrador':(41,490,191,649),'Dachshund':(212,490,370,649),'Husky':(390,490,545,649),'Bulldog':(571,490,723,649),'Terrier':(749,490,904,649)},
 'Dragonfly': {'Emperor Dragonfly':(42,774,235,951),'Broad-bodied Chaser':(269,774,459,951),'Southern Hawker':(487,774,679,951),'Common Darter':(708,774,911,951)},
 'Snail': {'Garden Snail':(49,1077,432,1218),'Grove Snail':(495,1077,877,1218)},
 'Spider': {'Wolf Spider':(39,1354,305,1530),'Crab Spider':(341,1354,581,1530),'Cellar Spider':(608,1354,904,1530)}
}
def place_approved_art():
 if not poster.exists():
  print('Approved poster not available; preserving generated illustrations');return 0
 sheet=Image.open(poster).convert('RGB');count=0
 for group,mapping in APPROVED_POSTER.items():
  for label,region in mapping.items():
   dest=f'{slug(group)}-{slug(label)}.webp'
   scene=Image.open(TARGETS[0]/dest).convert('RGB')
   piece=sheet.crop(region)
   if group=='Snail':
    piece=piece.resize((212,128),Image.Resampling.LANCZOS)
    base_mask=Image.new('L',piece.size,0)
    ImageDraw.Draw(base_mask).rounded_rectangle((0,0,piece.width-1,piece.height-1),radius=25,fill=255)
    origin=(14,61)
   else:
    side=202
    piece=ImageOps.fit(piece,(side,side),method=Image.Resampling.LANCZOS,centering=(.5,.5))
    base_mask=Image.new('L',(side,side),0)
    ImageDraw.Draw(base_mask).ellipse((3,3,side-4,side-4),fill=255)
    origin=((240-side)//2,(240-side)//2)
   # Isolate the illustrated animal from the poster's navy card background.
   # Avoid removing dark brown animal details or black eyes.
   px=np.asarray(piece).astype('int16')
   card=(px[:,:,2]-px[:,:,0]>13)&(px[:,:,2]-px[:,:,1]>10)&(px[:,:,0]<100)&(px[:,:,2]<115)
   final=np.asarray(base_mask).copy()
   final[card]=0
   final=Image.fromarray(final,'L').filter(ImageFilter.GaussianBlur(.65))
   scene.paste(piece,origin,final)
   for d in TARGETS:scene.save(d/dest,'WEBP',quality=93,method=4)
   count+=1
 print('Integrated',count,'approved reference illustrations with transparent poster borders')
 return count

if __name__=='__main__':
 generate()
 place_approved_art()
