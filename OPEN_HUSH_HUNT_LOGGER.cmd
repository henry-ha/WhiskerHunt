@echo off
rem Alternate persistent launcher: double-click this if BAT disappears.
cd /d "%~dp0"
title Hush Hunt Crash Logger - Persistent Console
cmd.exe /D /K ""%~dp0CAPTURE_AR_CRASH_LOG.bat""
