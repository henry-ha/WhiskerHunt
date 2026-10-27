@echo off
setlocal
cd /d "%~dp0"
set "PY=py -3"
where py >nul 2>&1
if errorlevel 1 set "PY=python"
:menu
cls
echo ============================================
echo HUSH HUNT - ALL 61 WILDLIFE ASSET SLOTS
 echo Review-first importer (never auto-overwrites)
echo ============================================
echo 1. See all 61 animal slots
 echo 2. Download 8 known direct GLBs into review folder
 echo 3. Audit progress and generate CSV
 echo 4. Stage your own licensed GLB for a slot
 echo 5. Approve inspected candidate
 echo 6. Dry-run ALL approved replacements
 echo 7. Install ALL approved with individual backups
 echo 8. Restore one animal from backup
 echo 9. Exit
set /p CHOICE=Select 1-9: 
if "%CHOICE%"=="1" goto list
if "%CHOICE%"=="2" goto fetch
if "%CHOICE%"=="3" goto audit
if "%CHOICE%"=="4" goto stage
if "%CHOICE%"=="5" goto approve
if "%CHOICE%"=="6" goto dryrun
if "%CHOICE%"=="7" goto install
if "%CHOICE%"=="8" goto restore
if "%CHOICE%"=="9" goto end
 echo Unknown choice
 goto pausemenu
:list
%PY% tools\hush_full_wildlife_upgrade.py list
goto pausemenu
:fetch
%PY% tools\hush_full_wildlife_upgrade.py fetch all
goto pausemenu
:audit
%PY% tools\hush_full_wildlife_upgrade.py audit
goto pausemenu
:dryrun
%PY% tools\hush_full_wildlife_upgrade.py install all --dry-run
goto pausemenu
:stage
 echo Enter exact slot (e.g. other-silverback-gorilla.glb)
set /p SLOT=Slot: 
 echo Full path to your licensed .glb
set /p ASSET=File path: 
set /p PUBLISHER=Source / creator name: 
set /p LICENCE=Licence or purchase rights: 
set /p WEBPAGE=Source page URL (optional): 
%PY% tools\hush_full_wildlife_upgrade.py stage "%SLOT%" "%ASSET%" --source "%PUBLISHER%" --license "%LICENCE%" --page "%WEBPAGE%"
goto pausemenu
:approve
 echo ONLY approve if you actually viewed the candidate in a GLB viewer and checked its licence, eyes, limbs, texture and proportions.
set /p SLOT=Exact model filename: 
set /p SURE=Do you confirm that review and licence? (type YES): 
if /I not "%SURE%"=="YES" goto menu
%PY% tools\hush_full_wildlife_upgrade.py approve "%SLOT%" --yes-i-reviewed-anatomy
goto pausemenu
:install
 echo WARNING: This will overwrite ONLY APPROVED slots in the current Visual Studio project, and create backups.
echo Your app's local user data is NOT modified. You must rebuild/deploy without uninstalling.
set /p SURE=To proceed, type INSTALL: 
if /I not "%SURE%"=="INSTALL" goto menu
%PY% tools\hush_full_wildlife_upgrade.py install all --yes
goto pausemenu
:restore
set /p SLOT=Exact model filename to restore: 
set /p SURE=Type RESTORE to confirm: 
if /I not "%SURE%"=="RESTORE" goto menu
%PY% tools\hush_full_wildlife_upgrade.py restore "%SLOT%" --yes
goto pausemenu
:pausemenu
 echo.
pause
goto menu
:end
endlocal
