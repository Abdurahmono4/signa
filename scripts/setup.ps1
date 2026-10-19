param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Test-Path 'backend/.venv/Scripts/python.exe')) {
        & $Python -m venv backend/.venv
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 ni o‘rnating yoki -Python bilan yo‘lini ko‘rsating.' }
    }
    & './backend/.venv/Scripts/python.exe' -m pip install -r backend/requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python kutubxonalari o‘rnatilmadi.' }
    npm.cmd --prefix frontend ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend kutubxonalari o‘rnatilmadi.' }
    Write-Output 'Tayyor. Endi npm run model, so‘ng npm start.'
} finally { Pop-Location }
