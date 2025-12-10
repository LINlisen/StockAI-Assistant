# StockAI-Assistant System Startup Script (PowerShell)
# This script starts Backend (FastAPI), Frontend (Streamlit), and Ollama services

param(
    [Parameter(Position = 0)]
    [string]$DbContainer = "postgres-container-custom-stockai",
    [switch]$h,
    [switch]$help,
    [switch]$skipOllama
)

# Show help message
function Show-Help {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "  StockAI-Assistant - Startup Script" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor White
    Write-Host "  .\startsys.ps1 [ContainerName] [Options]" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Options:" -ForegroundColor White
    Write-Host "  -h, -help        Show this help message" -ForegroundColor Gray
    Write-Host "  -skipOllama      Skip Ollama service startup" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor White
    Write-Host "  .\startsys.ps1              # Start all services" -ForegroundColor Gray
    Write-Host "  .\startsys.ps1 -help        # Show help" -ForegroundColor Gray
    Write-Host "  .\startsys.ps1 -skipOllama  # Start only backend and frontend" -ForegroundColor Gray
    Write-Host "  .\startsys.ps1 postgres-db  # Start with specific DB container" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Services:" -ForegroundColor White
    Write-Host "  Backend API (FastAPI)    - http://127.0.0.1:8000" -ForegroundColor Gray
    Write-Host "  Frontend (Streamlit)     - http://localhost:8501" -ForegroundColor Gray
    Write-Host "  Ollama Local AI          - http://localhost:11434" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Stop Services:" -ForegroundColor White
    Write-Host "  .\stopsys.ps1               # Stop all services" -ForegroundColor Gray
    Write-Host ""
    exit 0
}

# Check if help is requested
if ($h -or $help) {
    Show-Help
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  StockAI-Assistant - Starting..." -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Start Ollama service
if ($skipOllama) {
    Write-Host "[1/3] Skipping Ollama service (-skipOllama)" -ForegroundColor Yellow
}
else {
    Write-Host "[1/3] Starting Ollama service..." -ForegroundColor Blue

    $ollamaInstalled = Get-Command ollama -ErrorAction SilentlyContinue

    if ($ollamaInstalled) {
        $ollamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
        
        if ($ollamaProcess) {
            Write-Host "OK Ollama is already running" -ForegroundColor Green
        }
        else {
            Write-Host "Starting Ollama..."
            Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 3
            Write-Host "OK Ollama started (http://localhost:11434)" -ForegroundColor Green
        }
    }
    else {
        Write-Host "WARNING: Ollama not detected, skipping" -ForegroundColor Yellow
        Write-Host "  To use local AI models, install Ollama: https://ollama.ai" -ForegroundColor Gray
    }
}

Write-Host ""

# 2. Start Database (if specified)
# 2. Start Database (if specified)
if (-not [string]::IsNullOrEmpty($DbContainer)) {
    Write-Host "[2/3] Starting Database Container ($DbContainer)..." -ForegroundColor Blue
    
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        # --- Check Docker Daemon Status ---
        $dockerDaemonReady = $false
        docker info > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dockerDaemonReady = $true
        }
        else {
            Write-Host "Docker daemon is not running. Attempting to start Docker Desktop..." -ForegroundColor Yellow
            $dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
            
            if (Test-Path $dockerPath) {
                Start-Process -FilePath $dockerPath
                Write-Host "Launched Docker Desktop. Waiting for engine to initialize (this may take a minute)..." -ForegroundColor Gray
                
                # Wait loop (up to 90 seconds)
                $retries = 90
                while ($retries -gt 0) {
                    Write-Host "." -NoNewline -ForegroundColor Gray
                    Start-Sleep -Seconds 2
                    
                    docker info > $null 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "`nDocker Engine is ready!" -ForegroundColor Green
                        $dockerDaemonReady = $true
                        break
                    }
                    $retries -= 2
                }
                if (-not $dockerDaemonReady) {
                    Write-Host "`nTimed out waiting for Docker Engine." -ForegroundColor Red
                }
            }
            else {
                Write-Host "Could not find Docker Desktop at '$dockerPath'. Please start it manually." -ForegroundColor Red
            }
        }

        # --- Start Container ---
        if ($dockerDaemonReady) {
            $status = docker ps -a --filter "name=^/${DbContainer}$" --format "{{.Status}}"
            if ($status) {
                if ($status -match "Up") {
                    Write-Host "OK Database container is already running" -ForegroundColor Green
                }
                else {
                    Write-Host "Starting container..."
                    docker start $DbContainer
                    Write-Host "OK Database container started" -ForegroundColor Green
                }
            }
            else {
                # Update: If container not found, try to run docker-compose
                Write-Host "WARNING: Container '$DbContainer' not found." -ForegroundColor Yellow
                
                $composeFile = Join-Path $PSScriptRoot "dockerpg.yml"
                if (Test-Path $composeFile) {
                    Write-Host "Found '$composeFile'. Attempting to create and start container with docker-compose..." -ForegroundColor Blue
                    
                    # Run docker-compose
                    # Note: We use 'docker compose' (V2) or 'docker-compose' (V1)
                    if (Get-Command "docker-compose" -ErrorAction SilentlyContinue) {
                        docker-compose -f $composeFile up -d
                    }
                    else {
                        docker compose -f $composeFile up -d
                    }
                    
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "OK Database container created and started via docker-compose" -ForegroundColor Green
                    }
                    else {
                        Write-Host "ERROR: Failed to start with docker-compose" -ForegroundColor Red
                    }
                }
                else {
                    Write-Host "ERROR: '$composeFile' not found. Cannot auto-create container." -ForegroundColor Red
                }
            }
        }
    }
    else {
        Write-Host "WARNING: Docker command not found" -ForegroundColor Yellow
    }
    Write-Host ""
}

# 3. Start Backend API (FastAPI)
Write-Host "[2/3] Starting Backend API (FastAPI)..." -ForegroundColor Blue

$backendPath = Join-Path $PSScriptRoot "backend"

# Start backend in a new PowerShell window with cd to backend directory
$backendScript = "cd '$backendPath'; uvicorn main:app --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript

Write-Host "OK Backend starting in new window" -ForegroundColor Green
Write-Host "  API URL: http://127.0.0.1:8000" -ForegroundColor Gray
Write-Host "  API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Gray

Write-Host ""

# 3. Start Frontend (Streamlit)
Write-Host "[3/3] Starting Frontend (Streamlit)..." -ForegroundColor Blue

Start-Sleep -Seconds 2

$frontendPath = Join-Path $PSScriptRoot "frontend"

# Start frontend in a new PowerShell window with cd to frontend directory
$frontendScript = "cd '$frontendPath'; streamlit run app.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript

Write-Host "OK Frontend starting in new window" -ForegroundColor Green
Write-Host "  Frontend URL: http://localhost:8501" -ForegroundColor Gray

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "OK All services started successfully!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Service Status:" -ForegroundColor White
Write-Host "  Backend API:  http://127.0.0.1:8000" -ForegroundColor Gray
Write-Host "  Frontend:     http://localhost:8501" -ForegroundColor Gray
Write-Host "  Ollama:       http://localhost:11434" -ForegroundColor Gray
Write-Host ""

Write-Host "Instructions:" -ForegroundColor White
Write-Host "  1. Open browser: http://localhost:8501" -ForegroundColor Gray
Write-Host "  2. Register/Login" -ForegroundColor Gray
Write-Host "  3. Set Gemini API Key (or use Ollama)" -ForegroundColor Gray
Write-Host "  4. Start using AI trading analysis" -ForegroundColor Gray
Write-Host ""

Write-Host "To Stop Services:" -ForegroundColor Yellow
Write-Host "  Run .\stopsys.ps1 or close the service windows" -ForegroundColor Gray
Write-Host ""

Write-Host "Press any key to exit this window..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
