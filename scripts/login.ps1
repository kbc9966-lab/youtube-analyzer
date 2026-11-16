. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Installed

Write-Host 'Claude 구독 계정으로 로그인합니다. 브라우저가 열리면 로그인하고,'
Write-Host '화면에 나온 코드를 이 창에 붙여넣은 뒤 Enter를 눌러 주세요.'
Write-Host ''
& $ClaudeExe auth login --claudeai
Write-Host ''
& $ClaudeExe auth status
