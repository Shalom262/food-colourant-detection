$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Write-Host 'Open http://127.0.0.1:8000 after the server starts.'
& 'D:\powder dataset\.venv\Scripts\python.exe' app.py
