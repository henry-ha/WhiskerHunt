"""v2.2 regression: live performance, capture, retake and data compatibility.

Uses an actual canvas MediaStream in Chromium, not an Android camera/APK.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text().replace('<script src="app.js" defer></script>','').replace('<link rel="stylesheet" href="style.css">','')
        await page.set_content(html)
        await page.add_style_tag(content=(ROOT/'BrowserPreview/style.css').read_text())
        await page.add_script_tag(content=(ROOT/'BrowserPreview/app.js').read_text())
        await page.evaluate('''() => {
          window.__cats=new Map();window.__meta=new Map();
          window.openDb=async()=>({mock:true,transaction:(stores,mode)=>{
            const tx={objectStore:(store)=>({put:(value)=>{
              const m=store==='cats'?window.__cats:window.__meta;
              m.set(store==='cats'?value.id:value.key,value);
            }})};setTimeout(()=>tx.oncomplete?.(),0);return tx;
          }});
          window.transact=async(store,mode,method,value)=>{
            const m=store==='cats'?window.__cats:window.__meta;
            if(method==='getAll')return Array.from(m.values());
            if(method==='get')return m.get(value);
            if(method==='put'){m.set(store==='cats'?value.id:value.key,value);return value;}
            if(method==='delete'){m.delete(value);return;}
          };
          Object.defineProperty(window,'isSecureContext',{configurable:true,value:true});
          const canvas=document.createElement('canvas');canvas.width=800;canvas.height=450;
          const ctx=canvas.getContext('2d');let frame=0;
          window.__draw=setInterval(()=>{
            frame++;ctx.fillStyle=frame%2?'#65748c':'#718096';ctx.fillRect(0,0,800,450);
            ctx.fillStyle='#c99d7c';ctx.fillRect(230,95,300,270);
            ctx.fillStyle='#111923';ctx.fillRect(320,180,22,22);ctx.fillRect(430,180,22,22);
          },45);
          window.__canvas=canvas;window.__streams=[];
          Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{
            getUserMedia:async()=>{const stream=canvas.captureStream(25);window.__streams.push(stream);return stream;}
          }});
          window.__samples=0;window.__qualities=0;window.__frameSizes=[];
          const oldFrame=frameFromVideo,oldQuality=assessPhotoQuality;
          frameFromVideo=function(...args){window.__samples++;window.__frameSizes.push(args[1]);return oldFrame(...args)};
          assessPhotoQuality=function(...args){window.__qualities++;return oldQuality(...args)};
          boot();
        }''')
        await page.wait_for_function('window.whiskerBootComplete===true')
        await page.locator('#hero-catch').click()
        await page.locator('#live-photo').click()
        await page.locator('#encounter-video').wait_for(timeout=12000)
        await page.wait_for_function('liveCamera && liveCamera.frames.length>=1',timeout=12000)
        # The live preview must NOT do image quality assessment on each periodic sample.
        a=await page.evaluate('({samples:__samples,qualities:__qualities})')
        await page.wait_for_timeout(1150)
        b=await page.evaluate('({samples:__samples,qualities:__qualities})')
        assert b['samples']>a['samples'],(a,b)
        assert b['qualities']==a['qualities'],f'Preview still doing costly image quality analysis: {a}, {b}'
        assert max(await page.evaluate('__frameSizes'))<=520,'Live preview used expensive full-resolution frame sampling'
        # Circular tool icons, and a paw without a circular core background.
        styles=await page.evaluate('''() => ({
          pod:getComputedStyle(document.getElementById('tool-ball')).borderRadius,
          lure:getComputedStyle(document.getElementById('tool-lure')).borderRadius,
          core:getComputedStyle(document.querySelector('#throw-item .throw-pod-core')).backgroundImage,
          toes:document.querySelectorAll('#throw-item .paw-toe').length
        })''')
        assert styles['pod']=='50%' and styles['lure']=='50%',styles
        assert styles['core']=='none' and styles['toes']==4,styles
        await page.screenshot(path='/mnt/data/WhiskerHunt_v2.2_Preview.png',full_page=True)
        # Dragging suppresses periodic sampling and resumes afterwards.
        box=await page.locator('#throw-item').bounding_box()
        cx=box['x']+box['width']/2;cy=box['y']+box['height']/2
        await page.mouse.move(cx,cy);await page.mouse.down()
        await page.mouse.move(cx-25,cy-28)
        count=await page.evaluate('__samples')
        await page.wait_for_timeout(1200)
        assert await page.evaluate('__samples')==count,'Live sampling ran during drag'
        await page.mouse.up()
        await page.wait_for_timeout(1200)
        assert await page.evaluate('__samples')>count,'Sampling did not resume after drag'
        # Live retake must open a fresh MediaStream, not a native photo chooser.
        await page.locator('#encounter-retake').click()
        await page.wait_for_function('window.__streams.length>=2 && liveCamera && liveCamera.active',timeout=12000)
        assert await page.locator('#encounter-video').count()==1
        assert await page.evaluate('__streams[0].getVideoTracks()[0].readyState')=='ended'
        # Capturing should perform quality analysis once, select still and stop camera.
        await page.evaluate('handleEncounterHit("ball",.20)')
        await page.wait_for_function('s.encounterCaptured && liveCamera===null',timeout=15000)
        await page.locator('#encounter-continue').wait_for(timeout=10000)
        assert await page.evaluate('__qualities')>b['qualities']
        assert 720 in await page.evaluate('__frameSizes'),'No higher-resolution release photo was taken'
        assert await page.evaluate('s.captureSummary.quality.width>0')
        assert await page.evaluate('s.image.startsWith("data:image/jpeg;base64,")')
        assert await page.evaluate('__streams[1].getVideoTracks()[0].readyState')=='ended'
        assert await page.locator('#encounter-quality').get_by_text('Best of',exact=False).count()==1
        # CatDex and backup format are unchanged, including photo, XP and sightings.
        await page.locator('#encounter-continue').click()
        await page.locator('#cat-name').fill('Pawtest')
        await page.locator('#real-cat').check()
        await page.locator('#save-catch').click()
        await page.get_by_text('Pawtest',exact=True).first.wait_for()
        result=await page.evaluate('''() => ({
          cats:s.cats.length,sightings:s.cats[0].sightings.length,xp:s.profile.xp,
          photo:s.cats[0].photo.startsWith('data:image/jpeg;base64,'),
          backup:backupPayload(),database:DATABASE,dbVersion:DB_VERSION
        })''')
        assert result['cats']==1 and result['sightings']==1 and result['xp']>=100 and result['photo'],result
        assert result['backup']['version']==1 and len(result['backup']['cats'])==1
        assert result['database']=='whiskerhunt_local_v1' and result['dbVersion']==1
        # Stale capture selection must not overwrite a freshly reopened encounter.
        await page.locator('#nav-catch').click()
        await page.locator('#live-photo').click()
        await page.locator('#encounter-video').wait_for(timeout=12000)
        await page.evaluate('''() => {
          const old=chooseBestLiveFrameAtFocus;
          window.__oldChoose=old;
          chooseBestLiveFrameAtFocus=async(...args)=>{
            await new Promise(resolve=>setTimeout(resolve,250));return old(...args);
          };
          handleEncounterHit('ball',.25);
        }''')
        await page.locator('#encounter-retake').click()
        await page.wait_for_function('window.__streams.length>=4 && liveCamera?.active',timeout=12000)
        await page.wait_for_timeout(700)
        assert await page.locator('#encounter-video').count()==1
        assert await page.evaluate('s.encounterCaptured')==False
        assert await page.evaluate('s.cats.length')==1
        await page.evaluate('chooseBestLiveFrameAtFocus=window.__oldChoose')
        await page.locator('[data-close]').first.click()
        assert await page.evaluate('liveCamera===null')
        assert not errors,errors
        await page.evaluate('clearInterval(window.__draw)')
        await browser.close()
        print('PASS v2.2: preview-only JPEG sampling, drag pause/resume, live retake, capture and quality, CatDex backup compatibility, stale-result guard')

if __name__=='__main__':asyncio.run(main())
