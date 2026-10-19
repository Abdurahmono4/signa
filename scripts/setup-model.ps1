param([ValidateSet('small.en','medium.en','all')][string]$Model = 'all')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot 'backend'
Push-Location $backendPath
try {
    $selectedModels = if ($Model -eq 'all') { @('small.en','medium.en') } else { @($Model) }
    foreach ($selectedModel in $selectedModels) {
        & '.\.venv\Scripts\python.exe' -c "import sys; from huggingface_hub import snapshot_download; name=sys.argv[1]; snapshot_download('Systran/faster-whisper-'+name, local_dir='models/'+name, allow_patterns=['model.bin','config.json','tokenizer.json','vocabulary.txt'])" $selectedModel
        if ($LASTEXITCODE -ne 0) { throw 'Model yuklanmadi.' }
    }
} finally { Pop-Location }
