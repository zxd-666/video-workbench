$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistDir = Join-Path $Root "dist\video-workbench"
$ZipPath = Join-Path $Root "dist\video-workbench-windows-x64.zip"

Set-Location $Root

python -m PyInstaller --clean --noconfirm .\video-workbench.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $DistDir)) {
    throw "Build output not found: $DistDir"
}

if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

Compress-Archive -Path (Join-Path $DistDir "*") -DestinationPath $ZipPath -Force

Write-Host "Built: $ZipPath"
