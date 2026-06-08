# =============================================================================
# UPV-EARTH · launch.ps1
# Arranca toda la pila en local en Windows: Ollama + backend FastAPI + frontend.
#
#   .\launch.ps1           -> arranca en foreground (Ctrl+C detiene todo)
#   .\launch.ps1 stop      -> detiene los servicios lanzados con este script
#   .\launch.ps1 status    -> muestra el estado actual
#
# Requiere haber ejecutado antes:  .\setup.ps1
# =============================================================================

param(
    [ValidateSet("start","stop","status","restart")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"

$Root        = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$VenvDir     = Join-Path $Root ".venv"
$BackendDir  = Join-Path $Root "mockup\backend"
$FrontendDir = Join-Path $Root "mockup\frontend"
$RuntimeDir  = Join-Path $Root ".runtime"
$LogDir      = Join-Path $RuntimeDir "logs"
$PidDir      = Join-Path $RuntimeDir "pids"

$DbFile      = Join-Path $Root "mockup\data\seed\upvearth_local.db"
$UploadDir   = Join-Path $Root "mockup\data\uploads"
$PbCsv       = Join-Path $Root "corpus_PB\data\pb_reference.csv"

$BackendHost  = if ($env:BACKEND_HOST)  { $env:BACKEND_HOST }  else { "0.0.0.0" }
$BackendPort  = if ($env:BACKEND_PORT)  { [int]$env:BACKEND_PORT }  else { 8000 }
$FrontendHost = if ($env:FRONTEND_HOST) { $env:FRONTEND_HOST } else { "0.0.0.0" }
$FrontendPort = if ($env:FRONTEND_PORT) { [int]$env:FRONTEND_PORT } else { 3000 }
$OllamaModel  = if ($env:OLLAMA_MODEL)  { $env:OLLAMA_MODEL }  else { "qwen2.5:14b" }

New-Item -ItemType Directory -Force -Path $RuntimeDir, $LogDir, $PidDir, $UploadDir, (Split-Path $DbFile) | Out-Null

function Log     ($m) { Write-Host "[run ] $m" -ForegroundColor Cyan }
function Info-OK ($m) { Write-Host "[ ok ] $m" -ForegroundColor Green }
function Warn    ($m) { Write-Host "[warn] $m" -ForegroundColor Yellow }
function Err     ($m) { Write-Host "[err ] $m" -ForegroundColor Red }
function Have    ($c) { return [bool] (Get-Command $c -ErrorAction SilentlyContinue) }

function Read-Pid($file) {
    if (-not (Test-Path $file)) { return $null }
    try { return [int] (Get-Content $file -ErrorAction Stop).Trim() } catch { return $null }
}

function Is-Running($pidFile) {
    $procId = Read-Pid $pidFile
    if (-not $procId) { return $false }
    return [bool] (Get-Process -Id $procId -ErrorAction SilentlyContinue)
}

function Port-InUse($port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect("127.0.0.1", $port, $null, $null)
        $ok  = $iar.AsyncWaitHandle.WaitOne(500, $false)
        if ($ok -and $client.Connected) { return $true }
        return $false
    } catch { return $false }
    finally { $client.Close() }
}

function Wait-Http($url, $maxSeconds) {
    for ($i = 0; $i -lt $maxSeconds; $i++) {
        try {
            Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 -Uri $url | Out-Null
            return $true
        } catch { Start-Sleep -Seconds 1 }
    }
    return $false
}

function Preflight {
    if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
        Err "venv ausente. Ejecuta .\setup.ps1 primero."; exit 1
    }
    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Err "node_modules ausente. Ejecuta .\setup.ps1 primero."; exit 1
    }
    if (-not (Have "ollama")) {
        Warn "Ollama no encontrado en PATH. El chatbot y el scoring LLM no funcionarán."
    }
}

function Start-OllamaSvc {
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 -Uri "http://127.0.0.1:11434/api/tags" | Out-Null
        Info-OK "Ollama ya está corriendo"; return
    } catch {}
    if (-not (Have "ollama")) { Warn "Saltando Ollama (no instalado)"; return }
    Log "Arrancando Ollama..."
    $p = Start-Process -FilePath "ollama" -ArgumentList "serve" `
        -RedirectStandardOutput (Join-Path $LogDir "ollama.log") `
        -RedirectStandardError  (Join-Path $LogDir "ollama.err.log") `
        -PassThru -WindowStyle Hidden
    $p.Id | Out-File -FilePath (Join-Path $PidDir "ollama.pid") -Encoding ascii
    if (Wait-Http "http://127.0.0.1:11434/api/tags" 30) {
        Info-OK "Ollama listo (PID $($p.Id))"
    } else {
        Warn "Ollama no respondió. Revisa $LogDir\ollama.log"
    }
}

function Start-Backend {
    $pidFile = Join-Path $PidDir "backend.pid"
    if (Is-Running $pidFile) {
        Info-OK "Backend ya en ejecución (PID $(Read-Pid $pidFile))"; return
    }
    if (Port-InUse $BackendPort) {
        Warn "Puerto $BackendPort ocupado. Saltando backend."; return
    }
    Log "Arrancando backend FastAPI en puerto $BackendPort..."

    $py = Join-Path $VenvDir "Scripts\python.exe"
    $envVars = @{
        DATABASE_URL          = "sqlite:///$($DbFile -replace '\\','/')"
        UPLOAD_DIR            = $UploadDir
        PB_REFERENCE_CSV      = $PbCsv
        EMBEDDINGS_MODEL_NAME = if ($env:EMBEDDINGS_MODEL_NAME) { $env:EMBEDDINGS_MODEL_NAME } else { "sentence-transformers/allenai-specter" }
        LLM_ENABLED           = if ($env:LLM_ENABLED)         { $env:LLM_ENABLED }         else { "true" }
        OLLAMA_URL            = if ($env:OLLAMA_URL)          { $env:OLLAMA_URL }          else { "http://127.0.0.1:11434/api/generate" }
        OLLAMA_MODEL_NAME     = if ($env:OLLAMA_MODEL_NAME)   { $env:OLLAMA_MODEL_NAME }   else { $OllamaModel }
        LLM_TEMPERATURE       = if ($env:LLM_TEMPERATURE)     { $env:LLM_TEMPERATURE }     else { "0.0" }
        LLM_BASE_URL          = if ($env:LLM_BASE_URL)        { $env:LLM_BASE_URL }        else { "http://127.0.0.1:11434/v1" }
        LLM_MODEL             = if ($env:LLM_MODEL)           { $env:LLM_MODEL }           else { $OllamaModel }
        LLM_API_KEY           = if ($env:LLM_API_KEY)         { $env:LLM_API_KEY }         else { "ollama" }
        LLM_REQUEST_TIMEOUT   = if ($env:LLM_REQUEST_TIMEOUT) { $env:LLM_REQUEST_TIMEOUT } else { "180" }
        LLM_MAX_TOKENS        = if ($env:LLM_MAX_TOKENS)      { $env:LLM_MAX_TOKENS }      else { "512" }
        CHAT_TEMPERATURE      = if ($env:CHAT_TEMPERATURE)    { $env:CHAT_TEMPERATURE }    else { "0.2" }
    }
    foreach ($k in $envVars.Keys) { Set-Item -Path "Env:$k" -Value $envVars[$k] }

    $proc = Start-Process -FilePath $py `
        -ArgumentList @("-m","uvicorn","app.main:app","--host",$BackendHost,"--port",$BackendPort) `
        -WorkingDirectory $BackendDir `
        -RedirectStandardOutput (Join-Path $LogDir "backend.log") `
        -RedirectStandardError  (Join-Path $LogDir "backend.err.log") `
        -PassThru -WindowStyle Hidden
    $proc.Id | Out-File -FilePath $pidFile -Encoding ascii

    if (Wait-Http "http://127.0.0.1:$BackendPort/api/v1/health" 60) {
        Info-OK "Backend listo en http://localhost:$BackendPort  (PID $($proc.Id))"
    } else {
        Warn "Backend no respondió tras 60s. Revisa $LogDir\backend.log"
    }
}

function Start-Frontend {
    $pidFile = Join-Path $PidDir "frontend.pid"
    if (Is-Running $pidFile) {
        Info-OK "Frontend ya en ejecución (PID $(Read-Pid $pidFile))"; return
    }
    if (Port-InUse $FrontendPort) {
        Warn "Puerto $FrontendPort ocupado. Saltando frontend."; return
    }
    Log "Arrancando frontend Next.js en puerto $FrontendPort..."

    $env:NEXT_PUBLIC_API_BASE_URL  = if ($env:NEXT_PUBLIC_API_BASE_URL) { $env:NEXT_PUBLIC_API_BASE_URL } else { "/api/v1" }
    $env:API_BASE_URL_INTERNAL     = if ($env:API_BASE_URL_INTERNAL)    { $env:API_BASE_URL_INTERNAL }    else { "http://127.0.0.1:$BackendPort/api/v1" }

    $npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Path
    if (-not $npmCmd) { $npmCmd = (Get-Command npm).Path }

    $proc = Start-Process -FilePath $npmCmd `
        -ArgumentList @("run","dev","--","--hostname",$FrontendHost,"--port",$FrontendPort) `
        -WorkingDirectory $FrontendDir `
        -RedirectStandardOutput (Join-Path $LogDir "frontend.log") `
        -RedirectStandardError  (Join-Path $LogDir "frontend.err.log") `
        -PassThru -WindowStyle Hidden
    $proc.Id | Out-File -FilePath $pidFile -Encoding ascii

    if (Wait-Http "http://127.0.0.1:$FrontendPort" 90) {
        Info-OK "Frontend listo en http://localhost:$FrontendPort  (PID $($proc.Id))"
    } else {
        Warn "Frontend no respondió tras 90s. Revisa $LogDir\frontend.log"
    }
}

function Stop-One($pidFile, $name) {
    if (-not (Is-Running $pidFile)) {
        Log "$name no estaba corriendo."
        if (Test-Path $pidFile) { Remove-Item $pidFile -Force }
        return
    }
    $procId = Read-Pid $pidFile
    Log "Deteniendo $name (PID $procId)..."
    try { Stop-Process -Id $procId -Force -ErrorAction Stop } catch {}
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Info-OK "$name detenido."
}

function Do-Stop {
    Stop-One (Join-Path $PidDir "frontend.pid") "Frontend"
    Stop-One (Join-Path $PidDir "backend.pid")  "Backend"
    Stop-One (Join-Path $PidDir "ollama.pid")   "Ollama"
}

function Do-Status {
    $checks = @(
        @{ name="Ollama";   file=(Join-Path $PidDir "ollama.pid")   },
        @{ name="Backend";  file=(Join-Path $PidDir "backend.pid")  },
        @{ name="Frontend"; file=(Join-Path $PidDir "frontend.pid") }
    )
    foreach ($c in $checks) {
        if (Is-Running $c.file) { Info-OK ("{0,-8} RUNNING (PID {1})" -f $c.name, (Read-Pid $c.file)) }
        else                    { Warn   ("{0,-8} STOPPED" -f $c.name) }
    }
    Write-Host ""
    Write-Host "Logs: $LogDir\{ollama,backend,frontend}.log"
}

function Do-Start {
    Preflight
    Start-OllamaSvc
    Start-Backend
    Start-Frontend
    Write-Host ""
    Info-OK "Pila UPV-EARTH lista:"
    Write-Host "  · Frontend:  http://localhost:$FrontendPort"
    Write-Host "  · Backend:   http://localhost:$BackendPort  (health: /api/v1/health)"
    Write-Host "  · Ollama:    http://localhost:11434"
    Write-Host "  · Logs:      $LogDir\"
    Write-Host ""
    Log "Pulsa Ctrl+C para detener todos los servicios."
    try {
        while ($true) {
            Start-Sleep -Seconds 5
            if (-not (Is-Running (Join-Path $PidDir "backend.pid"))) {
                Err "Backend caído. Revisa $LogDir\backend.log"; Do-Stop; exit 1
            }
            if (-not (Is-Running (Join-Path $PidDir "frontend.pid"))) {
                Err "Frontend caído. Revisa $LogDir\frontend.log"; Do-Stop; exit 1
            }
        }
    } finally {
        Write-Host ""
        Log "Cerrando..."
        Do-Stop
    }
}

switch ($Action) {
    "start"   { Do-Start }
    "stop"    { Do-Stop }
    "status"  { Do-Status }
    "restart" { Do-Stop; Do-Start }
}
