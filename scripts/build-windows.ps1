$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Dist = Join-Path $Root "dist"
$ExeDist = Join-Path $Dist "windows"
$Spec = Join-Path $Root "packaging\bloom.spec"
$InnoScript = Join-Path $Root "packaging\installer.iss"

Write-Host "== Bloom Windows build =="
Write-Host "Root: $Root"

Write-Host "== Backend tests =="
Push-Location $Backend
& "$env:USERPROFILE\.local\bin\uv.exe" sync
& "$env:USERPROFILE\.local\bin\uv.exe" run pytest
Pop-Location

Write-Host "== Frontend build =="
Push-Location $Frontend
& npm.cmd install
& npm.cmd run build
Pop-Location

Write-Host "== PyInstaller build =="
Push-Location $Root
New-Item -ItemType Directory -Force -Path $Dist | Out-Null
New-Item -ItemType Directory -Force -Path $ExeDist | Out-Null
& "$env:USERPROFILE\.local\bin\uv.exe" run --project $Backend pyinstaller --noconfirm $Spec --distpath $ExeDist --workpath (Join-Path $Root "build\pyinstaller")
Pop-Location

Write-Host "Bloom.exe created at: $(Join-Path $ExeDist 'Bloom\Bloom.exe')"

$InnoCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) }

if ($InnoCandidates.Count -gt 0) {
    Write-Host "== Inno Setup installer =="
    $InnoCompiler = @($InnoCandidates)[0]
    & "$InnoCompiler" "$InnoScript"
    Write-Host "Installer output: $(Join-Path $Dist 'installer')"
} else {
    Write-Host "Inno Setup was not found. Install Inno Setup 6 and run:"
    Write-Host "  ISCC.exe $InnoScript"
}
