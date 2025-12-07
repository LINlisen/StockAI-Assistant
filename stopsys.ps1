# StockAI-Assistant System Stop Script (PowerShell)
# This script stops all related services

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  StockAI-Assistant - Stopping Services..." -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Stop Streamlit (Frontend)
Write-Host "[1/3] Stopping Frontend (Streamlit)..." -ForegroundColor Blue
$streamlitProcesses = Get-Process -Name "streamlit" -ErrorAction SilentlyContinue
if ($streamlitProcesses) {
    $streamlitProcesses | Stop-Process -Force
    Write-Host "OK Streamlit stopped" -ForegroundColor Green
} else {
    Write-Host "WARNING: No running Streamlit process found" -ForegroundColor Yellow
}

Write-Host ""

# Stop Uvicorn (Backend)
Write-Host "[2/3] Stopping Backend (Uvicorn)..." -ForegroundColor Blue
$uvicornProcesses = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
if ($uvicornProcesses) {
    $uvicornProcesses | Stop-Process -Force
    Write-Host "OK Uvicorn stopped" -ForegroundColor Green
} else {
    Write-Host "WARNING: No running Uvicorn process found" -ForegroundColor Yellow
}

Write-Host ""

# Stop Ollama (Optional)
Write-Host "[3/3] Stopping Ollama service..." -ForegroundColor Blue
$ollamaProcesses = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollamaProcesses) {
    $response = Read-Host "Do you want to stop Ollama service? (Y/N)"
    if ($response -eq "Y" -or $response -eq "y") {
        $ollamaProcesses | Stop-Process -Force
        Write-Host "OK Ollama stopped" -ForegroundColor Green
    } else {
        Write-Host "INFO: Ollama remains running" -ForegroundColor Cyan
    }
} else {
    Write-Host "WARNING: No running Ollama process found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "OK Services stopped!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
