"""v1.9: user-positioned focus region wins over misleading background detail."""
import asyncio,base64,io
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def sample(subject_sharp):
    w,h=640,480
    im=Image.new('RGB',(w,h),(135,135,135))
    d=ImageDraw.Draw(im)
    for y in range(0,h,8):
        for x in range(0,w,8):
            in_subject=220<=x<420 and 90<=y<290
            if in_subject==subject_sharp:
                v=45 if (x//8+y//8)%2 else 225
                d.rectangle((x,y,x+7,y+7),fill=(v,v,v))
    buf=io.BytesIO();im.save(buf,format='JPEG',quality=90)
    return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
  await page.set_content(html)
  await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
  await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
  photos=[sample(False),sample(True)]
  result=await page.evaluate('''async ([backgroundSharp,subjectSharp])=>{
    const a=await assessPhotoQuality(backgroundSharp),b=await assessPhotoQuality(subjectSharp);
    const frames=[{image:backgroundSharp,quality:a,at:1},{image:subjectSharp,quality:b,at:2}];
    const whole=chooseBestLiveFrame(frames).image===backgroundSharp?'background':'subject';
    const focused=await chooseBestLiveFrameAtFocus(frames,{x:.5,y:.4});
    const corner=await chooseBestLiveFrameAtFocus(frames,{x:.1,y:.1});
    return {whole,focused:focused.image===subjectSharp?'subject':'background',corner:corner.image===backgroundSharp?'background':'subject',
      focusScore:focused.subjectQuality.score,cornerScore:corner.subjectQuality.score,
      labels:[focused.subjectQuality.label,corner.subjectQuality.label]};
  }''',photos)
  print('Quality selection:',result)
  assert result['whole']=='background','Fixture must be misleading when scoring whole photo'
  assert result['focused']=='subject','Focused cat region should win'
  assert result['corner']=='background','Changing focus should change best frame'
  # A slow frame assessment must not overwrite the photo after camera shutdown.
  stale=await page.evaluate('''async (still)=>{
    s.image='unchanged-photo';
    const previous=chooseBestLiveFrameAtFocus;
    chooseBestLiveFrameAtFocus=async()=>{await new Promise(r=>setTimeout(r,70));return {image:still,quality:{score:99,label:'Clear-looking'}}};
    liveCamera={active:true,sampling:false,timer:null,stream:{getTracks:()=>[]},video:{readyState:0,pause:()=>{},srcObject:null},frames:[{image:still,quality:{score:99,label:'Clear-looking'},at:1}]};
    const pending=freezeLiveEncounter();
    await new Promise(r=>setTimeout(r,10));stopLiveCamera();await pending;
    chooseBestLiveFrameAtFocus=previous;
    return {image:s.image,session:liveCamera};
  }''',photos[0])
  assert stale=={'image':'unchanged-photo','session':None},stale
  assert not errors,errors
  print('PASS v1.9: focus-aware ranking, refocus, cancelled camera cannot overwrite saved photo')
  await browser.close()

if __name__=='__main__':asyncio.run(main())
