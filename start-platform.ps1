# BTC Quant Platform — PowerShell Launcher (Persistent)
# Usage: powershell -ExecutionPolicy Bypass -File start-platform.ps1

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  BTC Quant Trading Platform Launcher" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Kill any existing node processes on our ports
$existing = Get-NetTCPConnection -LocalPort 3000,8080 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($procId in $existing) {
    try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host "Killed process $procId" -ForegroundColor Yellow } catch {}
}

# Start Market Data Layer
Write-Host "[1/2] Starting Market Data Layer..." -ForegroundColor Green
$marketProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd `"$root\market-data`" && npx ts-node src/server.ts" -WindowStyle Minimized -PassThru
Write-Host "       PID: $($marketProc.Id) | WebSocket: ws://localhost:8080" -ForegroundColor Gray

Start-Sleep -Seconds 4

# Start Frontend
Write-Host "[2/2] Starting Frontend..." -ForegroundColor Green
$frontProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd `"$root\frontend`" && npx vite --host" -WindowStyle Minimized -PassThru
Write-Host "       PID: $($frontProc.Id) | URL: http://localhost:3000" -ForegroundColor Gray

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Yellow
Write-Host "  Market:   http://localhost:8081/health" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop: Close the minimized cmd windows, or run:" -ForegroundColor Gray
Write-Host "  Get-Process node | Stop-Process" -ForegroundColor Gray

# Open browser
Start-Process "http://localhost:3000"
