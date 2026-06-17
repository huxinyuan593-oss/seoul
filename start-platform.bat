@echo off
chcp 65001 >nul
title BTC 量化交易平台

echo ============================================
echo   BTC Quant Trading Platform Launcher
echo ============================================
echo.

:: Start Market Data (WebSocket + OHLCV)
echo [1/2] Starting Market Data Layer...
start "BTC-MarketData" /D "%~dp0market-data" cmd /c "npx ts-node src/server.ts"
echo        WebSocket: ws://localhost:8080
echo        HTTP:      http://localhost:8081

:: Wait a moment
timeout /t 3 /nobreak >nul

:: Start Frontend (Vite)
echo [2/2] Starting Frontend...
start "BTC-Frontend" /D "%~dp0frontend" cmd /c "npx vite --host"
echo        Frontend:  http://localhost:3000

echo.
echo ============================================
echo   All services started!
echo.
echo   Frontend:  http://localhost:3000
echo   Market:    http://localhost:8081/health
echo.
echo   Close this window to stop all services.
echo ============================================
pause
