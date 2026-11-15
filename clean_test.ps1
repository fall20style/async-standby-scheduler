# clean_test.ps1 — 캐시 전체 삭제 및 테스트 재시작 스크립트

# 콘솔 입출력 인코딩을 UTF-8로 설정하여 한글 깨짐 방지
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "1. 기존 캐시 폴더(__pycache__, .pytest_cache) 및 .pyc 파일을 삭제합니다..." -ForegroundColor Cyan

# .pytest_cache 삭제
if (Test-Path ".pytest_cache") {
    Remove-Item -Recurse -Force ".pytest_cache"
    Write-Host " - .pytest_cache 삭제 완료" -ForegroundColor Gray
}

# 하위 폴더를 포함한 모든 __pycache__ 폴더 삭제 (.venv 제외)
Get-ChildItem -Path . -Include "__pycache__" -Recurse -Force | Where-Object { $_.FullName -notlike "*\.venv\*" } | ForEach-Object {
    Remove-Item -Recurse -Force $_.FullName
    Write-Host " - $($_.FullName) 삭제 완료" -ForegroundColor Gray
}

# 남아있는 .pyc, .pyo 바이트코드 파일 삭제 (.venv 제외)
Get-ChildItem -Path . -Include "*.pyc", "*.pyo" -Recurse -Force | Where-Object { $_.FullName -notlike "*\.venv\*" } | ForEach-Object {
    Remove-Item -Force $_.FullName
}

Write-Host "`n2. 가상환경(.venv) 활성화 확인..." -ForegroundColor Cyan
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "[경고] .venv 폴더를 찾을 수 없습니다. 전역 Python 환경으로 진행합니다." -ForegroundColor Yellow
}

Write-Host "`n3. 캐시 없이 pytest 자동화 테스트를 새로 시작합니다...`n" -ForegroundColor Green
pytest -v --cache-clear
