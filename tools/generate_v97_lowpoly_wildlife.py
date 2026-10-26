"""Original, offline static species-shaped glTF assets for Hush Hunt. Distinct low-poly wildlife, not photogrammetry."""
import os, math, random, json
import numpy as np
import trimesh
from trimesh.visual.texture import TextureVisuals
from trimesh.visual.material import PBRMaterial
ROOT='/mnt/data/hush_v34_work/WhiskerHunt/Resources/Raw/ar_models'
random.seed(9)

def tint(color):
    h=color.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))+(255,)
def material(m,c):
    m.visual=TextureVisuals(material=PBRMaterial(baseColorFactor=tint(c),roughnessFactor=.82,metallicFactor=0, doubleSided=True))
    return m
class Model:
    def __init__(self):self.scene=trimesh.Scene();self.count=0;self.parts=[]
    def add(self,mesh,c):
        self.count+=1;self.parts.append((mesh,c));return self
    def oval(self,p,r,c,div=2):
        m=trimesh.creation.icosphere(subdivisions=div,radius=1);m.apply_scale(r);m.apply_translation(p);return self.add(m,c)
    def stick(self,a,b,rad,c,sections=9):
        a=np.array(a,dtype=float);b=np.array(b,dtype=float);v=b-a;d=np.linalg.norm(v)
        if d < .000001:return self
        m=trimesh.creation.cylinder(radius=rad,height=d,sections=sections)
        m.apply_transform(trimesh.geometry.align_vectors([0,0,1],v/d));m.apply_translation((a+b)/2)
        return self.add(m,c)
    def pointed(self,a,b,rad,c):
        a=np.array(a,dtype=float);b=np.array(b,dtype=float);v=b-a;d=np.linalg.norm(v)
        if d < .000001:return self
        m=trimesh.creation.cone(radius=rad,height=d,sections=9)
        m.apply_transform(trimesh.geometry.align_vectors([0,0,1],v/d));m.apply_translation(a)
        return self.add(m,c)
    def eye(self,x,y,z,r=.038):
        self.oval((x,y,z),(.99*r,.94*r,.7*r),'#100f13',3)
        self.oval((x-.010,y+.012,z+.017),(.25*r,.25*r,.12*r),'#ffffff',1)
        return self
    def save(self,filename):
        path=os.path.join(ROOT,filename)
        # Merge geometry sharing one solid material. Reduces ES2 draw calls,
        # critical for heavy spines, wings and small-phone AR frames.
        groups={}
        for m,c in self.parts:groups.setdefault(c,[]).append(m)
        for c,meshes in groups.items():
            merged=trimesh.util.concatenate(meshes)
            self.scene.add_geometry(material(merged,c),geom_name=f'material_{c.strip("#")}')
        blob=trimesh.exchange.gltf.export_glb(self.scene,include_normals=True)
        open(path,'wb').write(blob)
        return {'filename':filename,'size':len(blob),'meshes':self.count}

def mammal(kind):
    q=Model()
    palette={
        'fox':('#bd6030','#f5e9d3','#50312b'),
        'rabbit':('#8d7b66','#f1e9df','#514338'),
        'squirrel':('#99704f','#eee2cb','#493a31'),
        'dog':('#c1a27e','#e1c9a9','#483929'),
        'cat':('#b87b3d','#efe5c7','#4f322c'),
        'mouse':('#928d87','#f0e3d9','#615b55'),
        'deer':('#9b7146','#e5d4b7','#48362b'),
        'hedgehog':('#6d5646','#d4ad8b','#322e2b'),
        'bat':('#3d3a43','#a99793','#29232b')}
    fur,belly,dark=palette[kind]
    head_y=.56 if kind not in ('deer','hedgehog','bat') else (.86 if kind=='deer' else .38)
    if kind=='bat':
        q.oval((0,.32,0),(.20,.25,.17),fur).oval((0,.61,.08),(.17,.17,.14),fur)
        for sign in (-1,1):
            q.oval((sign*.41,.4,-.07),(.54,.055,.27),dark)
            q.pointed((sign*.11,.68,.02),(sign*.25,.92,.03),.09,fur)
            q.eye(sign*.09,.64,.205,.028)
        q.oval((0,.58,.24),(.07,.045,.03),belly)
        return q
    if kind=='hedgehog':
        q.oval((0,.33,-.12),(.38,.27,.48),dark,3)
        q.oval((0,.24,.22),(.26,.17,.25),belly)
        for i in range(140):
            theta=random.uniform(.05,math.pi*.94);phi=random.uniform(0,math.pi*2)
            xx=.36*math.sin(theta)*math.cos(phi); yy=.32+.245*abs(math.cos(theta));zz=-.15+.44*math.sin(theta)*math.sin(phi)
            if zz>.27:continue
            q.pointed((xx,yy,zz),(xx*1.28, yy+.16,zz*1.23),.035,fur)
        for s in (-1,1):
            q.eye(s*.135,.36,.40,.046)
            q.oval((s*.24,.12,.22),(.105,.085,.14),belly)
        q.oval((0,.27,.56),(.12,.09,.095),belly).oval((0,.32,.64),(.045,.036,.03),'#29252a')
        return q
    body_r =(.27,.25,.43) if kind in ('fox','dog','cat','rabbit') else (.20,.19,.31)
    if kind=='deer':body_r=(.32,.30,.56)
    q.oval((0,.40,-.10),body_r,fur,3)
    q.oval((0,.26,.14),(.17,.13,.27),belly,2)
    head_y =.86 if kind=='deer' else (.46 if kind=='mouse' else .68 if kind=='rabbit' else .57)
    head_z=.41 if kind!='deer' else .50
    head_r=(.21,.18,.20) if kind not in ('mouse','deer') else (.16,.16,.17)
    q.oval((0,head_y,head_z),head_r,fur,3)
    muzzle=(.115,.09,.14) if kind in ('dog','fox','deer') else (.09,.065,.11)
    q.oval((0,head_y-.05,head_z+.16),muzzle,belly)
    q.oval((0,head_y-.032,head_z+.30),(.034,.025,.032),dark,2)
    for sign in (-1,1):
        q.eye(sign*.112,head_y+.034,head_z+.145,.037)
        if kind=='rabbit':
            q.oval((sign*.115,head_y+.34,head_z-.025),(.071,.30,.053),fur,3)
            q.oval((sign*.115,head_y+.34,head_z+.023),(.035,.24,.017),'#b6847d')
        elif kind=='mouse':
            q.oval((sign*.17,head_y+.125,head_z-.08),(.10,.14,.055),fur)
            q.oval((sign*.17,head_y+.125,head_z-.03),(.067,.10,.019),'#bb928f')
        elif kind=='dog':
            q.oval((sign*.195,head_y-.12,head_z-.045),(.095,.165,.068),dark)
        elif kind in ('fox','cat'):
            q.pointed((sign*.14,head_y+.07,head_z-.06),(sign*.17,head_y+.36,head_z-.07),.11,fur)
            q.pointed((sign*.14,head_y+.12,head_z+.02),(sign*.165,head_y+.29,head_z+.01),.05,'#c58d87')
        elif kind=='deer':
            q.oval((sign*.22,head_y+.08,head_z-.04),(.18,.055,.105),fur)
            q.stick((sign*.08,head_y+.13,head_z-.08),(sign*.13,head_y+.44,head_z-.10),.034,dark)
            q.stick((sign*.13,head_y+.34,head_z-.10),(sign*.27,head_y+.52,head_z-.08),.022,dark)
            q.stick((sign*.12,head_y+.39,head_z-.10),(sign*.02,head_y+.55,head_z-.10),.018,dark)
    for x in (-.19,.19):
        for z in (-.35,.22):
            foot_y=.08; start=(x,.30,z);end=(x*1.12,foot_y,z+.05)
            if kind=='deer': start=(x,.42,z);end=(x,.035,z+.03)
            q.stick(start,end,.052 if kind!='mouse' else .030,fur)
            q.oval((end[0],foot_y,end[2]+.04),(.08,.045,.11),dark)
    if kind in ('fox','dog','cat','squirrel','mouse'):
        if kind=='squirrel':
            pts=[(0,.40,-.36),(.06,.52,-.62),(.12,.87,-.69),(.18,1.10,-.55),(.14,1.12,-.30)]
            for a,b in zip(pts,pts[1:]):q.stick(a,b,.11,fur)
            q.oval((.16,1.08,-.52),(.18,.28,.18),fur)
        elif kind=='fox':
            q.oval((0,.49,-.60),(.16,.14,.30),fur)
            q.oval((0,.46,-.85),(.11,.10,.17),belly)
        else:
            pts=[(0,.46,-.46),(.17,.60,-.60),(.28,.76,-.67)] if kind in ('cat','dog') else [(0,.40,-.37),(.22,.49,-.60)]
            for a,b in zip(pts,pts[1:]):q.stick(a,b,.055 if kind!='mouse' else .024,fur)
    if kind=='rabbit':q.oval((0,.43,-.52),(.13,.13,.15),belly)
    return q

def bug(kind):
    q=Model();leg='#2d2927';dark='#191c1d'
    if kind=='butterfly':
        q.oval((0,.40,0),(.063,.085,.34),'#342d31')
        for s in (-1,1):
            for z,sz,col in ((.18,.36,'#cb6047'),(-.21,.26,'#f1a85d')):
                q.oval((s*.30,.43,z),(.33,.030,sz),col,3)
                q.oval((s*.48,.46,z+.02),(.12,.024,.10),'#302e38')
                q.oval((s*.29,.464,z),(.11,.027,.10),'#f2d5a9')
            q.stick((s*.03,.46,.30),(s*.13,.62,.42),.018,dark)
        q.oval((0,.39,.34),(.067,.065,.075),'#26232d')
    elif kind=='bee':
        for z,c in ((-.28,'#e5a72c'),(-.08,dark),(.10,'#e6ae37'),(.25,dark)):
            q.oval((0,.38,z),(.22,.19,.18),c)
        q.oval((0,.40,.43),(.19,.18,.16),'#292521')
        for s in (-1,1):
            q.eye(s*.10,.48,.55,.032)
            q.oval((s*.25,.61,-.05),(.29,.022,.14),'#c8d8dc',3)
            for z in (-.20,.07,.27):
                q.stick((s*.17,.26,z),(s*.31,.07,z+.12),.015,leg)
            q.stick((s*.08,.52,.52),(s*.17,.66,.59),.015,leg)
    elif kind=='beetle':
        q.oval((0,.31,-.05),(.28,.19,.39),'#244a39',3)
        for s in (-1,1):
            q.oval((s*.13,.43,-.1),(.14,.09,.37),'#3c865c',3)
        q.stick((0,.52,-.43),(0,.50,.22),.012,'#1b3c32')
        q.oval((0,.32,.38),(.18,.14,.18),dark,3)
        for s in (-1,1):
            for z in (-.25,.01,.26):q.stick((s*.21,.25,z),(s*.42,.07,z+.09),.020,leg)
            q.stick((s*.11,.41,.52),(s*.18,.59,.64),.027,leg)
            q.stick((s*.07,.40,.55),(s*.14,.59,.63),.018,leg)
    elif kind=='dragonfly':
        q.oval((0,.41,-.12),(.048,.045,.52),'#409b9c',3)
        for z in (-.55,-.43,-.31,-.19):q.oval((0,.43,z),(.05,.055,.07),'#267082')
        q.oval((0,.45,.47),(.17,.15,.20),'#4b9687')
        for s in (-1,1):
            q.oval((s*.145,.51,.57),(.09,.10,.083),'#2e5669',3)
            for z in (-.07,.13):q.oval((s*.40,.51,z),(.42,.025,.11),'#b3d1c4',3)
            for z in (.10,.30):q.stick((s*.05,.37,z),(s*.19,.20,z+.03),.016,leg)
    elif kind=='ant':
        q.oval((0,.27,-.34),(.17,.16,.22),'#6c3d2d',3).oval((0,.27,.05),(.095,.12,.13),'#3d2826',3)
        q.oval((0,.30,.34),(.15,.145,.17),'#653828',3)
        for s in (-1,1):
            q.eye(s*.09,.34,.47,.024)
            for z in (-.1,.04,.18):
                q.stick((s*.08,.24,z),(s*.26,.13,z-.17),.017,leg)
                q.stick((s*.26,.13,z-.17),(s*.36,.05,z-.18),.014,leg)
            q.stick((s*.07,.38,.44),(s*.12,.55,.55),.012,leg)
    return q

def bird(kind):
    q=Model(); col='#806c59' if kind=='owl' else '#8a6552';bel='#e2c3aa' if kind=='owl' else '#bb512d'
    q.oval((0,.42,-.03),(.24,.34,.25),col,3).oval((0,.39,.18),(.18,.23,.10),bel)
    q.oval((0,.79,.12),(.20,.19,.19),col,3)
    for s in (-1,1):
        q.oval((s*.20,.47,-.08),(.11,.22,.15),'#53473c')
        q.eye(s*.092,.82,.283,.040 if kind=='robin' else .066)
        if kind=='owl':q.pointed((s*.11,.90,.07),(s*.20,1.05,.07),.10,col)
        q.stick((s*.1,.14,.05),(s*.11,.02,.12),.028,'#8a6643')
        for toe in (-.07,.04,.12):q.stick((s*.11,.02,.12),(s*.11+toe,.02,.21),.018,'#9b7545')
    q.pointed((0,.71,.24),(0,.70,.41),.07,'#d0a54d')
    q.oval((0,.45,-.34),(.10,.09,.27),col)
    return q

def frog():
    q=Model();green='#5d9951';dark='#436b38'
    q.oval((0,.20,0),(.36,.19,.36),green,3)
    q.oval((0,.21,.27),(.28,.15,.15),'#8baa61',3)
    for s in (-1,1):
        q.oval((s*.20,.35,.23),(.095,.10,.10),green)
        q.eye(s*.20,.37,.31,.062)
        q.oval((s*.33,.18,-.17),(.14,.14,.20),dark)
        q.stick((s*.28,.16,-.12),(s*.42,.05,.16),.045,green)
        for t in (-.04,.04,.11):q.stick((s*.42,.05,.16),(s*.42+t,.028,.28),.020,green)
    q.stick((-.13,.19,.40),(.13,.19,.40),.016,'#4c713d')
    return q

def tortoise():
    q=Model()
    q.oval((0,.22,0),(.39,.23,.44),'#4f5940',3)
    q.oval((0,.34,0),(.40,.245,.44),'#8a7450',3)
    for a in range(9):
        angle=2*math.pi*a/9
        x=.33*math.cos(angle);z=.34*math.sin(angle)
        q.oval((x,.46,z),(.095,.025,.11),'#625c3c')
    q.oval((0,.24,.49),(.17,.15,.21),'#849063',3)
    for s in (-1,1):
        q.eye(s*.09,.30,.66,.025)
        for z in (-.29,.27):q.oval((s*.30,.09,z),(.12,.09,.18),'#7c865d')
    return q

spec=[
 ('other-fox.glb','Other','Fox','🦊',lambda:mammal('fox')),
 ('rabbit-wild-rabbit.glb','Rabbit','Wild Rabbit','🐇',lambda:mammal('rabbit')),
 ('squirrel-grey-squirrel.glb','Squirrel','Grey Squirrel','🐿️',lambda:mammal('squirrel')),
 ('hedgehog-european-hedgehog.glb','Hedgehog','European Hedgehog','🦔',lambda:mammal('hedgehog')),
 ('frog-common-frog.glb','Frog','Common Frog','🐸',frog),
 ('dog-labrador.glb','Dog','Labrador','🐕',lambda:mammal('dog')),
 ('cat-ginger-tabby.glb','Cat','Ginger Tabby','🐈',lambda:mammal('cat')),
 ('bird-robin.glb','Bird','Robin','🐦',lambda:bird('robin')),
 ('bird-owl.glb','Bird','Owl','🦉',lambda:bird('owl')),
 ('butterfly-peacock.glb','Butterfly','Peacock','🦋',lambda:bug('butterfly')),
 ('bee-honeybee.glb','Bee','Honeybee','🐝',lambda:bug('bee')),
 ('beetle-stag-beetle.glb','Beetle','Stag Beetle','🪲',lambda:bug('beetle')),
 ('dragonfly-emperor-dragonfly.glb','Dragonfly','Emperor Dragonfly','🪷',lambda:bug('dragonfly')),
 ('ant-black-garden-ant.glb','Ant','Black Garden Ant','🐜',lambda:bug('ant')),
 ('other-deer.glb','Other','Deer','🦌',lambda:mammal('deer')),
 ('other-mouse.glb','Other','Mouse','🐁',lambda:mammal('mouse')),
 ('other-tortoise.glb','Other','Tortoise','🐢',tortoise),
 ('other-bat.glb','Other','Bat','🦇',lambda:mammal('bat')),
]
if __name__=='__main__':
    records=[]
    for file,group,name,emoji,f in spec:
        m=f();rec=m.save(file);rec.update(group=group,name=name,emoji=emoji)
        records.append(rec)
        print(file,rec['size'], 'meshes',rec['meshes'])
    open('/mnt/data/hush_v34_work/new_models.json','w').write(json.dumps(records,indent=2))

def ladybird():
    q=Model()
    # Oval wing-case, split into two glossy red hemispheres, correctly sized six legs.
    q.oval((0,.25,-.06),(.29,.16,.43),'#221c19',3)
    q.oval((0,.34,.28),(.225,.13,.18),'#161517',3)
    for side in (-1,1):
        q.oval((side*.142,.34,-.06),(.145,.19,.40),'#bc2f28',3)
        for x,y,z in ((.115,.505,.09),(.125,.500,-.20),(.18,.45,-.31)):
            q.oval((side*x,y,z),(.048,.017,.056),'#1e1716',2)
        q.oval((side*.16,.42,.38),(.09,.065,.055),'#eae4d4',2)
        q.eye(side*.13,.43,.42,.023)
        for z in (-.25,.02,.25):
            q.stick((side*.24,.24,z),(side*.36,.09,z+.07),.018,'#262023')
            q.stick((side*.36,.09,z+.07),(side*.42,.06,z+.14),.012,'#262023')
        q.stick((side*.075,.42,.43),(side*.15,.54,.51),.013,'#262023')
    q.stick((0,.54,-.39),(0,.54,.29),.010,'#1d1c1b')
    return q
