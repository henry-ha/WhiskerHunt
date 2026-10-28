#!/usr/bin/env python3
"""Offline top-down silhouette masks for uncompressed glTF GLB (stdlib only).
Losslessly leaves models unchanged. Unsupported compressed meshes are skipped.
"""
from __future__ import annotations
import json, math, struct, zlib
from pathlib import Path

DIM=128
MAX_TRIANGLES=9000

def matmul(a,b):
    return [sum(a[k*4+r]*b[c*4+k] for k in range(4)) for c in range(4) for r in range(4)]
def node_matrix(n):
    if len(n.get('matrix',[]))==16: return [float(v) for v in n['matrix']]
    x,y,z,w=n.get('rotation',[0,0,0,1]); sx,sy,sz=n.get('scale',[1,1,1]);tx,ty,tz=n.get('translation',[0,0,0]);
    return [(1-2*(y*y+z*z))*sx,(2*(x*y+z*w))*sx,(2*(x*z-y*w))*sx,0,
            (2*(x*y-z*w))*sy,(1-2*(x*x+z*z))*sy,(2*(y*z+x*w))*sy,0,
            (2*(x*z+y*w))*sz,(2*(y*z-x*w))*sz,(1-2*(x*x+y*y))*sz,0,
            tx,ty,tz,1]

def load_glb(path):
    with path.open('rb') as f:
        if f.read(4)!=b'glTF': raise ValueError('not GLB')
        version,length=struct.unpack('<II',f.read(8))
        if version!=2: raise ValueError('not glTF 2.0')
        chunks={}
        while f.tell()<length:
            head=f.read(8)
            if len(head)<8: break
            n,t=struct.unpack('<I4s',head)
            if n>200_000_000: raise ValueError('oversize')
            chunks[t]=f.read(n)
        data=json.loads(chunks[b'JSON'].decode('utf8'))
        return data,chunks.get(b'BIN\0',b'')

def accessor_values(g,buf,idx):
    a=g['accessors'][idx];v=g['bufferViews'][a['bufferView']]
    if v.get('buffer',0)!=0 or a.get('sparse'): raise ValueError('unsupported accessor')
    ty=a['componentType']; typ=a['type']; n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}.get(typ)
    fmt={5120:'b',5121:'B',5122:'h',5123:'H',5125:'I',5126:'f'}.get(ty)
    if not fmt or not n: raise ValueError('unsupported component')
    size=struct.calcsize('<'+fmt)*n
    stride=v.get('byteStride',size)
    offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    if offset+stride*(a['count']-1)+size>len(buf):raise ValueError('buffer overrun')
    return [struct.unpack_from('<'+fmt*n,buf,offset+i*stride) for i in range(a['count'])]

def triangles_for(g,b):
    nodes=g.get('nodes',[]); meshes=g.get('meshes',[]); scenes=g.get('scenes',[])
    scene=scenes[g.get('scene',0)] if scenes else {'nodes':list(range(len(nodes)))}
    identity=[1 if i%5==0 else 0 for i in range(16)]
    seen=set()
    positions=[]; triangles=[]
    def walk(idx,parent):
        if idx in seen or idx>=len(nodes): return
        seen.add(idx); node=nodes[idx]; trans=matmul(parent,node_matrix(node))
        if 'mesh' in node:
            for p in meshes[node['mesh']]['primitives']:
                if p.get('mode',4)!=4 or 'POSITION' not in p.get('attributes',{}):continue
                try:
                    verts=accessor_values(g,b,p['attributes']['POSITION'])
                    ids=[int(x[0]) for x in accessor_values(g,b,p['indices'])] if 'indices' in p else list(range(len(verts)))
                except (KeyError,ValueError,IndexError,struct.error):continue
                base=len(positions)
                for v in verts:
                    px,py,pz=v[:3];positions.append((trans[0]*px+trans[4]*py+trans[8]*pz+trans[12],trans[1]*px+trans[5]*py+trans[9]*pz+trans[13],trans[2]*px+trans[6]*py+trans[10]*pz+trans[14]))
                for k in range(0,len(ids)-2,3):
                    if max(ids[k:k+3])<len(verts):triangles.append((base+ids[k],base+ids[k+1],base+ids[k+2]))
        for child in node.get('children',[]):walk(child,trans)
    for idx in scene.get('nodes',[]):walk(idx,identity)
    if not positions:raise ValueError('no uncompressed triangle geometry')
    return positions,triangles

def hull(points):
    pts=sorted(set(points))
    if len(pts)<3: return pts
    def cross(o,a,b):return(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[];hi=[]
    for p in pts:
        while len(lo)>1 and cross(lo[-2],lo[-1],p)<=0:lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi)>1 and cross(hi[-2],hi[-1],p)<=0:hi.pop()
        hi.append(p)
    return lo[:-1]+hi[:-1]

def scan_polygon(mask,poly):
    if len(poly)<3:return
    ys=[y for _,y in poly]
    for y in range(max(0,int(math.floor(min(ys)))),min(DIM,int(math.ceil(max(ys)))+1)):
        inter=[]; at=y+.5
        for k in range(len(poly)):
            (x0,y0),(x1,y1)=poly[k],poly[(k+1)%len(poly)]
            if (y0<=at<y1) or (y1<=at<y0):inter.append(x0+(at-y0)*(x1-x0)/(y1-y0))
        inter.sort()
        for k in range(0,len(inter)-1,2):
            for x in range(max(0,int(math.floor(inter[k]))),min(DIM,int(math.ceil(inter[k+1]))+1)):
                if inter[k]<=x+.5<=inter[k+1]:mask[y*DIM+x]=255

def soften(arr):
    # two light Gaussian-like smoothing passes, keeps crisp species silhouette
    for axis in (0,1):
        out=bytearray(DIM*DIM)
        for y in range(DIM):
            for x in range(DIM):
                vals=[]
                for i,w in [(-2,1),(-1,4),(0,6),(1,4),(2,1)]:
                    ix,iy=(min(DIM-1,max(0,x+i)),y) if axis==0 else (x,min(DIM-1,max(0,y+i)))
                    vals.append(arr[iy*DIM+ix]*w)
                out[y*DIM+x]=sum(vals)//16
        arr=out
    return arr

def png_rgba(alpha):
    rows=b''.join(b'\0'+b''.join(bytes((0,0,0,a)) for a in alpha[y*DIM:(y+1)*DIM]) for y in range(DIM))
    def ck(t,content):return struct.pack('>I',len(content))+t+content+struct.pack('>I',zlib.crc32(t+content)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+ck(b'IHDR',struct.pack('>IIBBBBB',DIM,DIM,8,6,0,0,0))+ck(b'IDAT',zlib.compress(rows,7))+ck(b'IEND',b'')

def convert(source:Path,dest:Path):
    g,b=load_glb(source)
    points,tris=triangles_for(g,b)
    # Filament normalises to largest 3D dimension; so does the footprint texture.
    xyzmins=[min(p[k] for p in points) for k in range(3)]
    xyzmaxs=[max(p[k] for p in points) for k in range(3)]
    longest=max(.0001,*(xyzmaxs[i]-xyzmins[i] for i in range(3)))
    cx=(xyzmins[0]+xyzmaxs[0])*.5;cz=(xyzmins[2]+xyzmaxs[2])*.5
    pixel=0.90*(DIM-1)/longest
    proj=[((p[0]-cx)*pixel+DIM/2, (p[2]-cz)*pixel+DIM/2) for p in points]
    mask=bytearray(DIM*DIM)
    stride=max(1,math.ceil(len(tris)/MAX_TRIANGLES))
    for i in range(0,len(tris),stride):
        a,b,c=tris[i];scan_polygon(mask,[proj[a],proj[b],proj[c]])
    if sum(mask)<DIM*DIM:  # sparse fur geometry gets a filled outer footprint
        outer=hull(proj[::max(1,len(proj)//2000)])
        if sum(mask)<DIM*DIM*8:scan_polygon(mask,outer)
    if not any(mask): raise ValueError('empty shadow')
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(png_rgba(soften(mask)))

def generate(root:Path):
    src=root/'WhiskerHunt/Resources/Raw/ar_models'
    dst=root/'WhiskerHunt/Resources/Raw/ar_shadows'
    if not src.is_dir():raise FileNotFoundError(src)
    made=[];failed=[]
    for f in sorted(src.glob('*.glb')):
        try:
            out=dst/(f.stem+'.png')
            if out.exists() and out.stat().st_mtime >= f.stat().st_mtime:continue
            convert(f,out);made.append(f.name)
        except Exception as e:failed.append((f.name,str(e)))
    print('SILHOUETTES CREATED:',len(made),'ALREADY CURRENT:',len(list(dst.glob('*.png')))-len(made),'UNSUPPORTED:',len(failed))
    for f,msg in failed:print('SKIPPED',f,':',msg)
    return made,failed

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('project',type=Path,nargs='?',default=Path.cwd());args=ap.parse_args()
    generate(args.project)
