from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path
import cv2, numpy as np, shutil
root=Path('/mnt/data/hush_v3120_work')
centers={'arctic-fox-snowfall':650,'autumn-hare':610,'butterfly-garden':670,'forest-owl':570,'golden-eagle-peaks':560,'highland-stag':490,'lakeside-swan':650,'meadow-rabbit':650,'moonlit-badger':550,'mountain-deer':570,'puffin-cliffs':450,'red-panda-bamboo':620,'red-squirrel-glade':630,'river-otter':590,'robin-dawn':680,'twilight-fox':520,'waterfall-kingfisher':470,'wildflower-bee-meadow':650,'woodland-frog':650,'woodland-hedgehog':600}
widths={'mountain-deer':770,'highland-stag':770,'lakeside-swan':770,'golden-eagle-peaks':740,'butterfly-garden':680,'arctic-fox-snowfall':680,'waterfall-kingfisher':650,'puffin-cliffs':680,'wildflower-bee-meadow':680,'twilight-fox':630,'woodland-frog':640,'meadow-rabbit':640}
# Crop exclusively from the wildlife illustration, avoiding v82's blurred photo extensions.
# Fill portrait through a continuous non-Gaussian, non-panel geometric remap, no horizontal joins.
for name,cx in centers.items():
 src=np.array(Image.open(root/f'BrowserPreview/themes_v82/{name}.webp').convert('RGB'))
 y0,y1=493,1160
 width=widths.get(name,680)
 left=max(0,min(1200-width,cx-width//2))
 crop=src[y0:y1,left:left+width]
 H,W=1920,1080
 g=cv2.cvtColor(crop,cv2.COLOR_RGB2GRAY)
 gy=np.mean(np.abs(cv2.Sobel(g,cv2.CV_32F,0,1,ksize=3)),axis=1)
 low,high=np.percentile(gy,[12,90]); weight=2.2-1.0*np.clip((gy-low)/max(1e-3,high-low),0,1)
 weight[:85]*=1.14;weight[-90:]*=1.09
 boundaries=np.concatenate(([0.0],np.cumsum(weight))); boundaries*= (H-1)/boundaries[-1]
 ypos=np.interp(np.arange(H),boundaries,np.arange(len(crop)+1));
 mapy=np.tile(ypos.astype(np.float32)[:,None],(1,W));mapx=np.tile(np.linspace(0,width-1,W,dtype=np.float32)[None,:],(H,1))
 out=cv2.remap(crop,mapx,mapy,interpolation=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
 im=Image.fromarray(out,'RGB')
 # preserve edge detail; do not blur and never advertise native 4K fidelity
 im=ImageEnhance.Contrast(im).enhance(1.035)
 im=im.filter(ImageFilter.UnsharpMask(radius=0.75,percent=68,threshold=4))
 im=im.resize((2160,3840),Image.Resampling.LANCZOS)
 p=root/'BrowserPreview/themes_v83'/f'{name}.webp'
 im.save(p,format='WEBP',quality=90,method=5)
 small=im.resize((360,640),Image.Resampling.LANCZOS)
 small.save(root/'BrowserPreview/theme_previews_v83'/f'{name}.webp',format='WEBP',quality=88,method=5)
 for directory in ['themes_v83','theme_previews_v83']:
  shutil.copy2(root/'BrowserPreview'/directory/f'{name}.webp',root/'WhiskerHunt/Resources/Raw'/directory/f'{name}.webp')
 print(name,end=' ',flush=True)
print('\nFinished 20 continuous no-panel, no-blur wallpapers.')
