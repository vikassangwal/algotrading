@echo off
REM ELCO Trading Server — double-click to start (ya reboot ke baad).
REM Dashboard: http://localhost:8000  (password login)
REM Band karna ho: is window ko band kar do ya Ctrl+C.
cd /d "%~dp0"
title ELCO Trading Server
echo ============================================
echo   ELCO server shuru ho raha hai...
echo   Dashboard: http://localhost:8000
echo   (Ye window khuli rehne do - server isi me chalta hai)
echo ============================================
py -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
