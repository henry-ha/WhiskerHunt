@echo off
setlocal
cd /d "%~dp0"
echo Hush Hunt - Phoenix material depth fix: CHECK
where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0patch_phoenix_glb.py" --check --root "E:\inetpub\wwwroot\WhiskerHunt"
) else (
  python "%~dp0patch_phoenix_glb.py" --check --root "E:\inetpub\wwwroot\WhiskerHunt"
)
if errorlevel 1 (
 echo Operation FAILED. No source changes unless INSTALL explicitly passed.
) else (
 echo Operation finished.
)
pause
