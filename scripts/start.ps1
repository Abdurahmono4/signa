$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Split-Path $PSScriptRoot -Parent)).Path
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
$configPath = Join-Path $projectRoot 'frontend\vite.config.ts'
$frontendPath = Join-Path $projectRoot 'frontend'
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Python .venv topilmadi.' }
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if (!$nodeCommand) { throw 'Node.js topilmadi.' }
if (!(Test-Path -LiteralPath $vitePath)) { throw 'Avval frontend ichida npm install bajaring.' }
$runLogs = Join-Path $projectRoot 'storage\runs'
New-Item -ItemType Directory -Force -Path $runLogs | Out-Null
$runStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'

function Get-OwnedListener([int]$port, [string]$role) {
    $connections = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
    if (!$connections.Count) { return $null }
    $owners = @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -ne 1) { throw "Port $port bir nechta jarayonga tegishli. Jarayonlar o'zgartirilmadi." }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($owners[0])"
    if (!$process) { throw "Port $port egasini tekshirib bo'lmadi." }
    $command = [string]$process.CommandLine
    $rootInCommand = $command.IndexOf($projectRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0
    $roleMatches = if ($role -eq 'backend') {
        $command -match 'backend\.app\.main:app' -and $command -match '--port\s+8001\b'
    } else {
        $command.IndexOf($vitePath,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and $command -match '--port\s+5174\b'
    }
    if (!$rootInCommand -and $role -eq 'backend' -and $roleMatches) {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($process.ParentProcessId)" -ErrorAction SilentlyContinue
        $rootInCommand = $parent -and ([string]$parent.CommandLine).IndexOf($pythonPath,[StringComparison]::OrdinalIgnoreCase) -ge 0
    }
    if (!$rootInCommand -or !$roleMatches) { throw "Port $port boshqa yoki tasdiqlanmagan jarayonga tegishli. Uni to'xtatmadim." }
    return $process
}
function Test-Backend {
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8001/api/health' -TimeoutSec 2
        return ($health.ok -eq $true -and $health.device -eq 'cpu' -and $null -ne $health.verified_signs)
    } catch { return $false }
}
function Test-Frontend {
    try {
        $page = Invoke-WebRequest 'http://127.0.0.1:5174' -UseBasicParsing -TimeoutSec 2
        return ($page.StatusCode -eq 200 -and $page.Content -match 'SignBridge')
    } catch { return $false }
}

$backend = Get-OwnedListener 8001 'backend'
$frontend = Get-OwnedListener 5174 'frontend'
if ($backend -and !(Test-Backend)) { throw "Backend porti band, lekin health tekshiruvi o'tmadi. Mavjud jarayon to'xtatilmadi." }
if ($frontend -and !(Test-Frontend)) { throw "Frontend porti band, lekin sahifa tekshiruvi o'tmadi. Mavjud jarayon to'xtatilmadi." }
$backendStarted = $null; $frontendStarted = $null
if (!$backend) {
    $backendStarted = Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','backend.app.main:app','--app-dir',('"'+$projectRoot+'"'),'--host','127.0.0.1','--port','8001') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runLogs "backend-$runStamp.log") -RedirectStandardError (Join-Path $runLogs "backend-$runStamp-error.log")
    Write-Host 'Backend ishga tushirilmoqda...'
} else { Write-Host 'Backend allaqachon ishlayapti; qayta foydalaniladi.' }
if (!$frontend) {
    $frontendStarted = Start-Process -FilePath $nodeCommand.Source -ArgumentList @(('"'+$vitePath+'"'),'--config',('"'+$configPath+'"'),'--host','127.0.0.1','--port','5174','--strictPort',('"'+$frontendPath+'"')) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runLogs "frontend-$runStamp.log") -RedirectStandardError (Join-Path $runLogs "frontend-$runStamp-error.log")
    Write-Host 'Frontend ishga tushirilmoqda...'
} else { Write-Host 'Frontend allaqachon ishlayapti; qayta foydalaniladi.' }
$healthy = $false
for ($attempt=0; $attempt -lt 30; $attempt++) {
    if ((Test-Backend) -and (Test-Frontend)) { $healthy = $true; break }
    foreach ($started in @($backendStarted,$frontendStarted)) {
        if ($started) { $started.Refresh(); if ($started.HasExited) { throw "Server jarayoni erta tugadi. Jurnallar: $runLogs" } }
    }
    Start-Sleep -Milliseconds 500
}
if (!$healthy) { throw "Server ishga tushmadi. Jurnallar: $runLogs" }
$backend = Get-OwnedListener 8001 'backend'; $frontend = Get-OwnedListener 5174 'frontend'
@{backend=$backend.ProcessId;frontend=$frontend.ProcessId;project_root=$projectRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot 'storage\server-pids.json')
Write-Host 'SignBridge UZ: http://127.0.0.1:5174'
Write-Host 'API: http://127.0.0.1:8001/docs'
Write-Host 'Tekshirish: .venv\Scripts\python.exe scripts\check-local-readiness.py'
if ($env:SIGNBRIDGE_NO_BROWSER -ne '1') { Start-Process 'http://127.0.0.1:5174' }
