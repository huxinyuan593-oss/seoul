@echo off
chcp 65001 >nul
title BTC Trading Platform [PRODUCTION]
cd /d "%~dp0"

echo ============================================
echo   BTC Quant Trading Platform
echo   Production Mode - Stable
echo ============================================
echo.

:: Build frontend if not already built
if not exist "frontend\dist\index.html" (
    echo [BUILD] Building frontend...
    cd frontend
    call npx vite build
    cd ..
)

:: Kill existing node processes on our ports
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000.*LISTENING" 2^>nul') do (
    taskkill /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080.*LISTENING" 2^>nul') do (
    taskkill /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8081.*LISTENING" 2^>nul') do (
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul

:: Start Market Data Server
echo [1/2] Starting Market Data Server (WebSocket + News)...
start "BTC-MarketData" /D "%~dp0market-data" cmd /c "npx ts-node src/server.ts"
timeout /t 4 /nobreak >nul

:: Start Frontend (Production Static Server - NO Vite dev)
echo [2/2] Starting Frontend (Production Mode)...
start "BTC-Frontend" /D "%~dp0frontend" cmd /c "node server.cjs"
timeout /t 2 /nobreak >nul

:: Open browser
start chrome http://localhost:3000 2>nul
start http://localhost:3000 2>nul

echo.
echo ============================================
echo   Platform is LIVE:
echo.
echo   Frontend : http://localhost:3000
echo   API News : http://localhost:8081/news
echo   WS Data  : ws://localhost:8080
echo.
echo   This window: safe to close
echo   Server windows: minimize, don't close
echo ============================================
pause
