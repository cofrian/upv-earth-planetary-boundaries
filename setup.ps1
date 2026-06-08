# =============================================================================
# UPV-EARTH · setup.ps1
# Bootstrap completo en Windows desde un sistema sin nada instalado.
#
#   .\setup.ps1   -> instala/verifica dependencias y prepara el proyecto
#   .\launch.ps1  -> arranca backend + frontend + Ollama
#
# Requisitos del sistema: Windows 10/11 con winget (App Installer) y permisos
# normales de usuario. Para algunas instalaciones puede solicitar elevación.
# =============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"

$Root        = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$VenvDir     = Join-Path $Root ".venv"
$BackendDir  = Join-Path $Root "mockup\backend"
$FrontendDir = Join-Path $Root "mockup\frontend"
$EnvFile     = Join-Path $Root "mockup\.env"
$EnvExample  = Join-Path $Root "mockup\.env.example"
$RuntimeDir  = Join-Path $Root ".runtime"
$LogDir      = Join-Path $RuntimeDir "logs"
$PidDir      = Join-Path $RuntimeDir "pids"

$PyMinMajor    = 3
$PyMinMinor    = 11
$NodeMinMajor  = 20
$OllamaModel   = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "qwen2.5:14b" }

function Log    ($msg) { Write-Host "[setup] $msg" -ForegroundColor Cyan }
function Info-OK($msg) { Write-Host "[ ok ] $msg" -ForegroundColor Green }
function Warn   ($msg) { Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Err    ($msg) { Write-Host "[err ] $msg" -ForegroundColor Red }

function Have($cmd) {
    return [bool] (Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user    = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Ensure-Winget {
    if (Have "winget") { Info-OK "winget disponible"; return }
    Err "winget (App Installer) no está instalado. Instálalo desde Microsoft Store y vuelve a ejecutar este script."
    exit 1
}

function Install-WingetPackage($id, $friendly) {
    Log "Instalando $friendly ($id) vía winget..."
    winget install --id $id --silent --accept-source-agreements --accept-package-agreements --scope machine
    if ($LASTEXITCODE -ne 0) {
        Warn "Reintentando $id en scope user..."
        winget install --id $id --silent --accept-source-agreements --accept-package-agreements --scope user
    }
    Refresh-Path
}

function Get-PythonExe {
    foreach ($cmd in @("py", "python")) {
        if (Have $cmd) {
            try {
                $ver = (& $cmd -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null)
                if ($ver) { $ver = ($ver -join "").Trim() }
                if ($ver -eq "$PyMinMajor.$PyMinMinor") { return @{ Cmd = $cmd; Args = @() } }
            } catch {}
        }
    }
    if (Have "py") {
        try {
            $list = (& py "-0" 2>$null) -join "`n"
            if ($list -match "-V:?$PyMinMajor\.$PyMinMinor") {
                return @{ Cmd = "py"; Args = @("-$PyMinMajor.$PyMinMinor") }
            }
        } catch {}
    }
    return $null
}

function Invoke-Python {
    param([string[]]$ExtraArgs)
    $allArgs = @()
    if ($Script:PyArgs -and $Script:PyArgs.Count -gt 0) { $allArgs += $Script:PyArgs }
    $allArgs += $ExtraArgs
    & $Script:PyCmd @allArgs
}

function Ensure-Python {
    $py = Get-PythonExe
    if ($py) {
        $Script:PyCmd  = $py.Cmd
        $Script:PyArgs = $py.Args
        $v = Invoke-Python @("--version")
        Info-OK "Python OK: $v ($($Script:PyCmd) $($Script:PyArgs -join ' '))"
        return
    }
    Install-WingetPackage "Python.Python.$PyMinMajor.$PyMinMinor" "Python $PyMinMajor.$PyMinMinor"
    $py = Get-PythonExe
    if (-not $py) { Err "Python $PyMinMajor.$PyMinMinor no quedó disponible tras la instalación."; exit 1 }
    $Script:PyCmd  = $py.Cmd
    $Script:PyArgs = $py.Args
    $v = Invoke-Python @("--version")
    Info-OK "Python instalado: $v"
}

function Ensure-Node {
    if (Have "node") {
        $v = (& node -v).TrimStart('v')
        $major = [int]($v.Split('.')[0])
        if ($major -ge $NodeMinMajor) {
            Info-OK "Node OK: v$v  ·  npm $(& npm -v)"
            return
        }
        Warn "Node v$v detectado, se necesita >= $NodeMinMajor"
    }
    Install-WingetPackage "OpenJS.NodeJS.LTS" "Node.js LTS"
    if (-not (Have "node")) {
        Err "Node no quedó disponible tras la instalación. Cierra y vuelve a abrir PowerShell."
        exit 1
    }
    Info-OK "Node instalado: $(& node -v)"
}

function Ensure-Ollama {
    if (Have "ollama") {
        Info-OK "Ollama presente"
        return
    }
    Install-WingetPackage "Ollama.Ollama" "Ollama"
    if (-not (Have "ollama")) {
        Warn "Ollama no quedó en PATH. Reinicia PowerShell y vuelve a ejecutar setup."
        return
    }
    Info-OK "Ollama instalado"
}

function Start-OllamaBg {
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 -Uri "http://127.0.0.1:11434/api/tags" | Out-Null
        Info-OK "Servicio Ollama ya corriendo"
        return
    } catch {}

    if (-not (Have "ollama")) { Warn "Ollama no disponible, saltando arranque"; return }

    Log "Arrancando 'ollama serve' en segundo plano..."
    $proc = Start-Process -FilePath "ollama" -ArgumentList "serve" `
        -RedirectStandardOutput (Join-Path $LogDir "ollama.log") `
        -RedirectStandardError  (Join-Path $LogDir "ollama.err.log") `
        -PassThru -WindowStyle Hidden
    $proc.Id | Out-File -FilePath (Join-Path $PidDir "ollama.pid") -Encoding ascii

    for ($i = 0; $i -lt 30; $i++) {
        try {
            Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 -Uri "http://127.0.0.1:11434/api/tags" | Out-Null
            Info-OK "Ollama listo (PID $($proc.Id))"
            return
        } catch { Start-Sleep -Seconds 1 }
    }
    Warn "Ollama no respondió en 30s. Revisa $LogDir\ollama.log"
}

function Pull-OllamaModel {
    if (-not (Have "ollama")) { Warn "Ollama no disponible, no se descarga modelo."; return }
    Log "Comprobando modelo Ollama '$OllamaModel' (puede ser una descarga grande)..."
    $list = & ollama list 2>$null
    if ($list -match [Regex]::Escape($OllamaModel)) {
        Info-OK "Modelo '$OllamaModel' ya descargado"
        return
    }
    & ollama pull $OllamaModel
    if ($LASTEXITCODE -eq 0) {
        Info-OK "Modelo '$OllamaModel' descargado"
    } else {
        Warn "No se pudo descargar '$OllamaModel'. Reintenta luego con: ollama pull $OllamaModel"
    }
}

function Ensure-Venv {
    if (Test-Path (Join-Path $VenvDir "Scripts\python.exe")) {
        Info-OK "venv existente en $VenvDir"
        return
    }
    if (Test-Path $VenvDir) {
        Warn "Eliminando venv inválido en $VenvDir"
        Remove-Item -Recurse -Force $VenvDir
    }
    Log "Creando venv en $VenvDir..."
    Invoke-Python @("-m","venv",$VenvDir)
    Info-OK "venv creado"
}

function Install-BackendDeps {
    Log "Instalando dependencias del backend..."
    $py = Join-Path $VenvDir "Scripts\python.exe"
    & $py -m pip install --upgrade pip wheel setuptools
    & $py -m pip install -r (Join-Path $BackendDir "requirements.txt")
    Info-OK "Dependencias backend instaladas"
}

function Install-FrontendDeps {
    Log "Instalando dependencias del frontend (npm install)..."
    Push-Location $FrontendDir
    try {
        & npm install --no-audit --no-fund
    } finally {
        Pop-Location
    }
    Info-OK "Dependencias frontend instaladas"
}

function Ensure-EnvFile {
    if (Test-Path $EnvFile) { Info-OK ".env ya presente"; return }
    Copy-Item -Path $EnvExample -Destination $EnvFile
    Info-OK ".env creado a partir de .env.example"
}

# --- Main --------------------------------------------------------------------

New-Item -ItemType Directory -Force -Path $RuntimeDir, $LogDir, $PidDir | Out-Null
Log "Iniciando setup de UPV-EARTH en $Root"

Ensure-Winget
Ensure-Python
Ensure-Node
Ensure-Ollama
Ensure-Venv
Install-BackendDeps
Install-FrontendDeps
Ensure-EnvFile
Start-OllamaBg
Pull-OllamaModel

Info-OK "Setup completado. Ahora arranca la app con:  .\launch.ps1"
