"""Original textured ARCore demonstration meshes: a garden slug and a garden spider.
Not scans/photogrammetry; do not represent them as wildlife-grade anatomical reconstructions.
CC0 original procedural geometry and textures generated for Hush Hunt.
"""
from pathlib import Path
import runpy
import numpy as np
import trimesh
from PIL import Image
src = runpy.run_path(str(Path(__file__).with_name('generate_starter_models.py')))
tex, ball, tube, add = [src[k] for k in ('tex','mesh_uv_sphere','tapered_tube','add')]
out=Path(__file__).resolve().parents[1]/'WhiskerHunt'/'Resources'/'Raw'/'ar_models'

def sphere(scene,name,center,radii,img,seg=48,lat=28):
    add(scene, ball(center,radii,img,(seg,lat)),name)

def slug():
    scene=trimesh.Scene()
    cocoa=tex((124,90,58),'skin',512)
    tan=tex((168,132,97),'skin',512)
    dark=tex((39,32,26),'skin',256)
    sphere(scene,'long tapered body',[0,.054,-.055],[.105,.054,.225],cocoa,64,36)
    sphere(scene,'mantle',[0,.096,.035],[.094,.052,.116],tan)
    sphere(scene,'slender forward head',[0,.075,.171],[.066,.056,.069],cocoa)
    # A pointed tail without a shell is a distinguishing slug feature.
    tubepts=[[0,.056,-.20],[0,.045,-.265],[0,.031,-.314],[0,.020,-.356]]
    add(scene,tube(tubepts,[.078,.050,.025,.004],cocoa,22),'tapered tail')
    for side in (-1,1):
        pts=[[side*.043,.104,.195],[side*.061,.15,.220],[side*.078,.203,.239]]
        add(scene,tube(pts,[.008,.006,.005],tan,14),'eyestalk'+str(side))
        sphere(scene,'eye tip'+str(side),pts[-1],[.011,.011,.011],dark,20,14)
        pts2=[[side*.034,.075,.205],[side*.057,.073,.239],[side*.066,.072,.259]]
        add(scene,tube(pts2,[.005,.003,.0015],tan,12),'lower tentacle'+str(side))
        # side markings
        for z in [-.10,-.04,.015,.07]:
            sphere(scene,f'mottled spot {side} {z}',[side*.092,.107,z],[.0025,.008,.012],dark,12,8)
    data=scene.export(file_type='glb'); (out/'other-slug.glb').write_bytes(data)
    print('other-slug.glb',len(data),len(scene.geometry))

def spider():
    scene=trimesh.Scene()
    brown=tex((107,78,57),'skin',512)
    tan=tex((155,124,94),'skin',512)
    dark=tex((41,31,26),'skin',256)
    cream=tex((194,164,129),'skin',256)
    sphere(scene,'patterned round abdomen',[0,.105,-.087],[.085,.070,.113],brown,60,36)
    sphere(scene,'cephalothorax',[0,.102,.074],[.070,.045,.075],tan)
    sphere(scene,'head',[0,.103,.125],[.050,.036,.034],brown)
    for side in (-1,1):
        for i,z in enumerate([.125,.064,.015,-.04]):
            start=np.array([side*.05,.112,z]); outward=(.18,.22,.24,.20)[i]
            knee=np.array([side*outward,.166 if i<2 else .145,z+(.13,.035,-.06,-.15)[i]])
            foot=np.array([side*(outward+.12),.015,z+(.18,.045,-.10,-.24)[i]])
            add(scene,tube([start.tolist(),((start+knee)/2).tolist(),knee.tolist(),((knee+foot)/2).tolist(),foot.tolist()], [.010,.010,.008,.006,.0025],brown,12),f'leg {side} {i+1}')
            sphere(scene,f'leg joint {side} {i}',knee,[.011,.011,.011],dark,12,8)
        for i,z in enumerate([.08,.11]):
            sphere(scene,'small marking '+str(side)+str(i),[side*(.050-.012*i),.162,-.080+z],[.005,.006,.009],cream,12,9)
        add(scene,tube([[side*.021,.114,.142],[side*.043,.105,.166],[side*.048,.087,.175]],[.007,.005,.002],tan,10),'pedipalp'+str(side))
        for x,y,z in [(side*.030,.117,.157),(side*.016,.125,.16)]:
            sphere(scene,'eye '+str(side)+str(x),[x,y,z],[.007,.007,.007],dark,14,10)
    # contrasting pale abdominal markings
    for zz in [-.15,-.11,-.07,-.03]:
        sphere(scene,f'abdominal stripe {zz}',[0,.173,zz],[.04,.002,.008],cream,24,12)
    data=scene.export(file_type='glb'); (out/'spider-garden-spider.glb').write_bytes(data)
    print('spider-garden-spider.glb',len(data),len(scene.geometry))

slug(); spider()
