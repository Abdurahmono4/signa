$ErrorActionPreference = 'Stop'
$projectRoot=(Resolve-Path -LiteralPath (Split-Path $PSScriptRoot -Parent)).Path
$pythonPath=Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath=Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
foreach ($entry in @(@{port=8001;role='backend'},@{port=5174;role='frontend'})) {
    $connections=@(Get-NetTCPConnection -State Listen -LocalPort $entry.port -ErrorAction SilentlyContinue)
    foreach ($serverId in @($connections | Select-Object -ExpandProperty OwningProcess -Unique)) {
        $process=Get-CimInstance Win32_Process -Filter "ProcessId=$serverId"
        if (!$process) { continue }
        $command=[string]$process.CommandLine
        $rootMatches=$command.IndexOf($projectRoot,[StringComparison]::OrdinalIgnoreCase) -ge 0
        $roleMatches=if ($entry.role -eq 'backend') {
            $command -match 'backend\.app\.main:app' -and $command -match '--port\s+8001\b'
        } else {
            $command.IndexOf($vitePath,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and $command -match '--port\s+5174\b'
        }
        if (!$rootMatches -and $entry.role -eq 'backend' -and $roleMatches) {
            $parent=Get-CimInstance Win32_Process -Filter "ProcessId=$($process.ParentProcessId)" -ErrorAction SilentlyContinue
            $rootMatches=$parent -and ([string]$parent.CommandLine).IndexOf($pythonPath,[StringComparison]::OrdinalIgnoreCase) -ge 0
        }
        if (!$rootMatches -or !$roleMatches) { Write-Warning "Port $($entry.port) boshqa yoki tasdiqlanmagan jarayonga tegishli; to'xtatilmadi."; continue }
        Stop-Process -Id $serverId
        Write-Host "$($entry.role) to'xtatildi."
    }
}
