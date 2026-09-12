$ErrorActionPreference = 'Stop'
$recipePython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $recipePython)) {
    throw 'Set up the Python environment using README.md first.'
}
Write-Host 'Open http://localhost:8000 to use Epicure. Press Ctrl+C to stop.'
& $recipePython -m uvicorn app:app --app-dir (Join-Path $PSScriptRoot 'backend') --host 127.0.0.1 --port 8000
