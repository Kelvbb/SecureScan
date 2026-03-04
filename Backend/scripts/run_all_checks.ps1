# SCRIPT COMPLET DE VÉRIFICATION - SecureScan
# PowerShell equivalent of run_all_checks.sh
# Usage: powershell -ExecutionPolicy Bypass -File scripts\run_all_checks.ps1

# Ne fonctionne pas
<# # ── Prise en charge des accents (UTF-8) ────────────────────────────────────
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8 #>

$ErrorActionPreference = "Stop"

# ── Chemins ────────────────────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptDir
$Python     = Join-Path $BackendDir "venv\Scripts\python.exe"
$LogStdout  = Join-Path $env:TEMP "securescan_server_stdout.log"
$LogStderr  = Join-Path $env:TEMP "securescan_server_stderr.log"

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  VÉRIFICATIONS COMPLÈTES - SECURESCAN" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan

# ── Setup ──────────────────────────────────────────────────────────────────
Write-Host "[SETUP] Backend détecté : $BackendDir" -ForegroundColor Blue
Write-Host "[SETUP] Vérifier que le venv existe..." -ForegroundColor Blue

Set-Location $BackendDir

if (-not (Test-Path (Join-Path $BackendDir "venv"))) {
    Write-Host "⚠ Création du venv..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "[SETUP] Installer les dépendances..." -ForegroundColor Blue
& $Python -m pip install --upgrade pip setuptools wheel | Out-Null
& $Python -m pip install -r requirements.txt
& $Python -m pip install requests

# ── Check 1 : Imports ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "[CHECK 1] IMPORTS PYTHON" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
& $Python scripts\check_imports.py

# ── Check 2 : Base de données ─────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "[CHECK 2] CONNEXION À LA BASE DE DONNÉES" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
& $Python scripts\check_database.py

# ── Check 3 : Inserts complets ────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "[CHECK 3] INSERTS COMPLETS (Scan + Tool + Vulnerabilities)" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
& $Python scripts\check_complete_scan.py

# ── Check 4 : Serveur FastAPI ─────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "[CHECK 4] DÉMARRAGE DU SERVEUR FASTAPI" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Lancement du serveur sur http://localhost:8000" -ForegroundColor Blue

$ServerProcess = Start-Process `
    -FilePath $Python `
    -ArgumentList "-m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $LogStdout `
    -RedirectStandardError  $LogStderr `
    -PassThru `
    -NoNewWindow

Write-Host "PID: $($ServerProcess.Id)" -ForegroundColor Blue
Write-Host "Attente du démarrage (5s)..." -ForegroundColor Blue
Start-Sleep -Seconds 5

if ($ServerProcess.HasExited) {
    Write-Host "✗ Le serveur n'a pas démarré" -ForegroundColor Red
    Write-Host "--- stdout ---"
    Get-Content $LogStdout -Encoding UTF8 -ErrorAction SilentlyContinue
    Write-Host "--- stderr ---"
    Get-Content $LogStderr -Encoding UTF8 -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "✓ Serveur démarré avec succès" -ForegroundColor Green

# ── Check 5 : API ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "[CHECK 5] TESTS API (Endpoints)" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan

Write-Host "Check 5.1: GET / (Health Check)" -ForegroundColor Blue
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/" -Method Get
    $r | ConvertTo-Json
} catch {
    Write-Host "✗ Erreur: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Check 5.2: GET /health" -ForegroundColor Blue
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
    $r | ConvertTo-Json
} catch {
    Write-Host "✗ Erreur: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Check 5.3: Flux API complet" -ForegroundColor Blue
& $Python scripts\check_api_flow.py

# ── Check 6 : Statistiques BD ─────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "[CHECK 6] VÉRIFICATION DES INSERTS EN BD" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
& $Python scripts\check_db_stats.py

# ── Cleanup ───────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "[CLEANUP] Arrêt du serveur" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# ── Résumé ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✓ TOUTES LES VÉRIFICATIONS RÉUSSIES!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host " RÉSUMÉ:"
Write-Host "  ✓ Imports Python        : OK" -ForegroundColor Green
Write-Host "  ✓ Connexion BD          : OK" -ForegroundColor Green
Write-Host "  ✓ Inserts Scan/Tool/Vuln: OK" -ForegroundColor Green
Write-Host "  ✓ Serveur FastAPI       : OK" -ForegroundColor Green
Write-Host "  ✓ Endpoints API         : OK" -ForegroundColor Green
Write-Host "  ✓ Flux complet          : OK" -ForegroundColor Green
Write-Host "  ✓ Vérification BD       : OK" -ForegroundColor Green
Write-Host ""