param(
    [switch]$RuntimeOnly,
    [switch]$SkipRuntime,
    [ValidateRange(1,16)][int]$Workers = 6
)
$ErrorActionPreference = 'Stop'
if ($RuntimeOnly -and $SkipRuntime) { throw 'RuntimeOnly and SkipRuntime cannot be combined.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
$modelRoot = Join-Path $projectRoot 'backend/models/MaDiS'
$sourceRoot = Join-Path $modelRoot 'source'
$runtimeRoot = Join-Path $modelRoot 'runtime'
$runtimePython = Join-Path $runtimeRoot '.venv/Scripts/python.exe'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'neural-model-manifest.json') -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $modelRoot, $runtimeRoot | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot '.git'))) {
    if ((Test-Path -LiteralPath $sourceRoot) -and (Get-ChildItem -LiteralPath $sourceRoot -Force | Select-Object -First 1)) {
        throw 'The source directory contains unrelated files. It was preserved.'
    }
    & git clone --filter=blob:none --no-checkout $manifest.source_repository $sourceRoot
    if ($LASTEXITCODE -ne 0) { throw 'Official MaDiS source download failed.' }
    & git -C $sourceRoot checkout --detach $manifest.source_commit
    if ($LASTEXITCODE -ne 0) { throw 'Pinned MaDiS source checkout failed.' }
}
$actualCommit = & git -C $sourceRoot rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actualCommit.Trim() -ne $manifest.source_commit) {
    throw 'The source revision differs from the pinned release. Existing files were preserved.'
}
if (-not $SkipRuntime) {
    if (-not (Test-Path -LiteralPath $runtimePython)) {
        & py -3.11 -m venv (Join-Path $runtimeRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Install 64-bit Python 3.11, then retry.' }
    }
    & $runtimePython -m pip install --upgrade 'pip==26.2.1' --timeout 90 --retries 3
    if ($LASTEXITCODE -ne 0) { throw 'Isolated pip setup failed.' }
    & $runtimePython (Join-Path $PSScriptRoot 'download-neural-model.py') --model-root $modelRoot --torch --workers $Workers
    if ($LASTEXITCODE -ne 0) { throw 'Verified CPU Torch download failed. Retry resumes completed ranges.' }
    & $runtimePython -m pip install (Join-Path $runtimeRoot ('wheels/' + $manifest.torch.path)) --timeout 90 --retries 3
    if ($LASTEXITCODE -ne 0) { throw 'CPU Torch installation failed.' }
    & $runtimePython -m pip install -r (Join-Path $PSScriptRoot 'neural-runtime-requirements.txt') --timeout 90 --retries 3
    if ($LASTEXITCODE -ne 0) { throw 'Isolated generation dependencies could not be installed.' }
    & $runtimePython (Join-Path $PSScriptRoot 'verify-neural-runtime.py') --model-root $modelRoot
    if ($LASTEXITCODE -ne 0) { throw 'CPU model import/forward verification failed.' }
}
if (-not $RuntimeOnly) {
    if (-not (Test-Path -LiteralPath $runtimePython)) { throw 'Create the isolated runtime first.' }
    & $runtimePython (Join-Path $PSScriptRoot 'download-neural-model.py') --model-root $modelRoot --workers $Workers
    if ($LASTEXITCODE -ne 0) { throw 'Model download or checksum validation failed. Retry resumes completed ranges.' }
}
Write-Output 'MaDiS CPU setup complete. Whisper and its environment were not modified.'
