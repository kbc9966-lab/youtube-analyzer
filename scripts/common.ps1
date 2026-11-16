# 설치·실행·로그인 스크립트가 같이 쓰는 경로
# 가상환경은 컴퓨터마다 따로, OneDrive 밖(사용자 폴더)에 만든다. 동기화로 서로 덮어쓰지 않게.
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$AppDir = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $env:USERPROFILE '.youtube-analyzer\venv'
$VenvPython = Join-Path $Venv 'Scripts\python.exe'
$ClaudeExe = Join-Path $Venv 'Lib\site-packages\claude_agent_sdk\_bundled\claude.exe'

function Assert-Installed {
    if (-not (Test-Path $VenvPython)) {
        Write-Host '이 컴퓨터에는 아직 설치가 안 되어 있어요. 설치.bat 을 먼저 실행해 주세요.' -ForegroundColor Yellow
        exit 1
    }
}
