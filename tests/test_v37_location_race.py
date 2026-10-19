"""v3.5: native GPS request tagging, approximate pins and Android asset consistency."""
import asyncio, re
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]

async def main():
    project=(ROOT/'WhiskerHunt/WhiskerHunt.csproj').read_text()
    xaml=(ROOT/'WhiskerHunt/MainPage.xaml').read_text()
    native=(ROOT/'WhiskerHunt/MainPage.xaml.cs').read_text()
    assert '<ApplicationDisplayVersion>3.5.0</ApplicationDisplayVersion>' in project
    assert '<ApplicationVersion>37</ApplicationVersion>' in project
    assert 'Source="index_v37.html"' in xaml
    assert 'GetLocationAsync(GetQuery(request, "request"))' in native
    assert 'Math.Round(position.Latitude, 2' in native
    assert 'Math.Round(position.Longitude, 2' in native
    assert 'whiskerNativeLocationError?.({safeToken})' in native
    for directory in [ROOT/'BrowserPreview',ROOT/'WhiskerHunt/Resources/Raw']:
        assert (directory/'app_v37.js').read_bytes()==(directory/'app.js').read_bytes()
        assert (directory/'style_v37.css').read_bytes()==(directory/'style.css').read_bytes()
        entry=(directory/'index_v37.html').read_text()
        assert 'app_v37.js' in entry and 'style_v37.css' in entry
    source=(ROOT/'BrowserPreview/app.js').read_text()
    assert "const WHISKER_BUILD='3.5.0'" in source
    native_call="location.href='whiskerhunt://location?request='+encodeURIComponent(token)"
    assert native_call in source
    # Browser simulation uses a tiny hook in place of custom-protocol navigation;
    # all real GPS request/callback logic runs unchanged.
    mock_source=source.replace(native_call,'window.__locationRequests.push(token)')
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':390,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'BrowserPreview/index.html').read_text()
        html=re.sub(r'<script\s+src="[^"]+"\s+defer></script>','',html)
        html=re.sub(r'<link\s+rel="stylesheet"\s+href="[^"]+">','',html)
        await page.set_content(html)
        await page.add_script_tag(content=mock_source)
        result=await page.evaluate('''async () => {
          window.__locationRequests=[];
          window.whiskerNativeReady=true;
          const one=locationPrompt();
          const two=locationPrompt();
          const tokens=window.__locationRequests.slice();
          const first=await one;
          // This stale native callback arrives after a newer permission prompt.
          window.whiskerNativeLocation(11.123456,12.654321,tokens[0]);
          const stillActive=activeLocationFinish!==null;
          window.whiskerNativeLocation(51.54321,-0.13254,tokens[1]);
          const second=await two;
          return {tokens,first,stillActive,second,
              callbackCleared:window.whiskerNativeLocation===null};
        }''')
        assert len(result['tokens'])==2 and len(set(result['tokens']))==2,result
        assert result['first'] is None,result
        assert result['stillActive'] is True,result
        assert result['second']=={'lat':51.54,'lng':-0.13},result
        assert result['callbackCleared'] is True,result
        await page.evaluate('''() => {
          s.pendingApproxLocation={lat:51.54,lng:-0.13};
          s.pendingApproxLocationAt=Date.now();
          s.storageBlocked=false;s.busy=false;s.cats=[];
          startCatch();
        }''')
        assert await page.evaluate('s.pendingApproxLocation===null') is True
        assert not errors,errors
        await browser.close()
        print('PASS v3.5: GPS requests distinguish stale callbacks, round coordinates, and clear consent for new catches')

if __name__=='__main__': asyncio.run(main())
