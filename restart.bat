@echo off
chcp 65001 >nul
title Restart BTC Platform
cd /d "%~dp0"

echo 正在重启 BTC 交易平台...

:: Kill existing
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Start via PowerShell (truly independent processes)
powershell -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %cd%\market-data && npx ts-node src\server.ts' -WindowState Minimized"
timeout /t 4 /nobreak >nul
powershell -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %cd%\frontend && node server.cjs' -WindowState Minimized"
timeout /t 3 /nobreak >nul

:: Open browser
start chrome http://localhost:3000 2>nul

echo.
echo ====================================
echo  平台已重启!
echo  http://localhost:3000
echo ====================================
pause
