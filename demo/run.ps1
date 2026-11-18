$ErrorActionPreference = 'Stop'
$demoPath = $PSScriptRoot
wsl -d Ubuntu-22.04 --cd "$demoPath" -- .venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Demo could not start. Follow demo/README.md to set up its WSL environment.'
    exit $LASTEXITCODE
}
