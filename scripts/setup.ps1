. (Join-Path $PSScriptRoot 'common.ps1')

Write-Host '============================================'
Write-Host ' 유튜브 분석기 설치'
Write-Host '============================================'
Write-Host ''

# 1. Python 3.12 찾기, 없으면 설치
$py312 = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $found = & py -3.12 -c 'import sys; print(sys.executable)' 2>$null
    if ($LASTEXITCODE -eq 0 -and $found) { $python = $found.Trim() }
}
if (-not $python -and (Test-Path $py312)) { $python = $py312 }
if (-not $python) {
    Write-Host '[1/3] Python 3.12를 설치합니다. 몇 분 걸릴 수 있어요...'
    winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements --silent
    if (Test-Path $py312) { $python = $py312 }
}
if (-not $python) {
    Write-Host ''
    Write-Host 'Python 설치에 실패했어요. https://www.python.org/downloads/ 에서 Python 3.12를 직접 설치한 뒤 다시 실행해 주세요.' -ForegroundColor Red
    exit 1
}
Write-Host "[1/3] Python 확인: $python"

# 2. 가상환경 만들기
if (Test-Path $VenvPython) {
    Write-Host "[2/3] 가상환경이 이미 있어요: $Venv"
} else {
    Write-Host "[2/3] 가상환경을 만듭니다: $Venv"
    & $python -m venv $Venv
    if ($LASTEXITCODE -ne 0) { Write-Host '가상환경을 만들지 못했어요.' -ForegroundColor Red; exit 1 }
}

# 3. 패키지 설치 (yt-dlp는 유튜브 변경에 맞춰 최신으로 올린다)
Write-Host '[3/3] 필요한 패키지를 설치합니다...'
& $VenvPython -m pip install -q --upgrade pip
& $VenvPython -m pip install -q --upgrade -r (Join-Path $AppDir 'requirements.txt')
if ($LASTEXITCODE -ne 0) { Write-Host '패키지 설치 중 오류가 났어요. 위의 메시지를 확인해 주세요.' -ForegroundColor Red; exit 1 }

Write-Host ''
Write-Host '설치가 끝났어요.' -ForegroundColor Green
Write-Host '처음이면 로그인.bat 으로 Claude 로그인을 한 다음, 실행.bat 으로 시작하세요.'
