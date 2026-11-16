. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Installed

Set-Location $AppDir
Start-Process 'http://127.0.0.1:5000'
& $VenvPython app.py
