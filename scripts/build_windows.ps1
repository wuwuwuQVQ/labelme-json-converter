$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BuildRoot = Join-Path $ProjectRoot "build\windows-x86_64"
$DistRoot = Join-Path $ProjectRoot "dist-release\windows-x86_64"
$ReleaseRoot = Join-Path $ProjectRoot "dist-release"
$ExePath = Join-Path $DistRoot "Labelme-JSON-Converter.exe"
$ArchivePath = Join-Path $ReleaseRoot "Labelme-JSON-Converter-Windows-x86_64.zip"

if (-not [Environment]::Is64BitOperatingSystem) {
    throw "Windows 首版只支持 x86_64。"
}

New-Item -ItemType Directory -Force -Path "$BuildRoot\spec", "$BuildRoot\work", "$BuildRoot\config", $DistRoot | Out-Null
$env:PYINSTALLER_CONFIG_DIR = "$BuildRoot\config"
$env:PYTHONPATH = "$ProjectRoot\src"

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "Labelme-JSON-Converter" `
    --distpath $DistRoot `
    --workpath "$BuildRoot\work" `
    --specpath "$BuildRoot\spec" `
    "$ProjectRoot\packaging\launcher.py"

$CoreProcess = Start-Process -FilePath $ExePath -ArgumentList "--self-test" -Wait -PassThru
if ($CoreProcess.ExitCode -ne 0) {
    throw "Windows 封装程序核心自检失败，退出码：$($CoreProcess.ExitCode)"
}
$UiProcess = Start-Process -FilePath $ExePath -ArgumentList "--ui-smoke-test" -Wait -PassThru
if ($UiProcess.ExitCode -ne 0) {
    throw "Windows 封装程序 GUI 烟雾测试失败，退出码：$($UiProcess.ExitCode)"
}

if (Test-Path $ArchivePath) {
    Remove-Item -Force $ArchivePath
}
Compress-Archive -LiteralPath $ExePath -DestinationPath $ArchivePath -CompressionLevel Optimal
Add-Type -AssemblyName System.IO.Compression.FileSystem
$Zip = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
try {
    if ($Zip.Entries.Count -ne 1 -or $Zip.Entries[0].Length -le 0) {
        throw "Windows ZIP 内容不完整。"
    }
} finally {
    $Zip.Dispose()
}
Write-Host "Windows 成品：$ArchivePath"

