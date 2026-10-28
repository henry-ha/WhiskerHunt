Hush Hunt v3.10.36 B99 - SurfaceView PixelCopy Compile Hotfix
===============================================================

WHY THIS PATCH IS NEEDED
The earlier smoother AR+shadow installer changed the renderer's overlay from
TextureView to SurfaceView, but kept a TextureView-only .getBitmap(96,96) call.
That causes JAVA0000 and XAJVC0000 in HushFilamentOverlay.java, around line 516.

WHAT THIS DOES
Only patches HushFilamentOverlay.java. Changes the synchronous getBitmap()
visibility sampling to asynchronous PixelCopy.request(SurfaceView,...).
Preserves the pixel scorer, logging, visual-readiness rule, animal GLBs,
ARCore logic, controls and existing saves. Pixel copying stops after the HD
model has passed visibility validation, as before.

INSTALL ON WINDOWS
1. CLOSE Visual Studio or stop debugging.
2. Extract ALL files into your WhiskerHunt solution directory (the directory
   containing WhiskerHunt.sln), e.g. E:\inetpub\wwwroot\WhiskerHunt.
3. Run CHECK_PIXELCOPY_FIX.cmd. It must display CHECK PASSED.
4. Run INSTALL_PIXELCOPY_FIX.cmd. It must display INSTALL COMPLETED.
5. Open Visual Studio > Build > Clean Solution > Rebuild Solution.
6. Deploy to your connected Android phone without uninstalling the app.

ROLLBACK
Run ROLLBACK_PIXELCOPY_FIX.cmd to restore the most recent pre-hotfix Java
source from the backup directory HushHunt_PixelCopy_Hotfix_Backups.

IMPORTANT
This fixes the visible Java build error. It does NOT prove smoothness or
shadow shape on a physical device. Those still need real-world tests.
The installer deliberately refuses to change unfamiliar source layouts.
It does not modify your installed app, GLB files or saved wildlife data.
