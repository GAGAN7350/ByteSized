Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$vsixPath = Join-Path $scriptDir "blueprintbob-0.1.0.vsix"
$sharedDir = Resolve-Path (Join-Path $scriptDir "..\shared")

if (-not (Test-Path $vsixPath)) {
    Write-Error "VSIX not found at $vsixPath"
    exit 1
}

$zip = [System.IO.Compression.ZipFile]::Open($vsixPath, [System.IO.Compression.ZipArchiveMode]::Update)

$files = @(
    "package.json",
    "out/index.js",
    "out/index.d.ts",
    "out/apiClient.js",
    "out/apiClient.d.ts",
    "out/statusBar.js",
    "out/statusBar.d.ts"
)

foreach ($f in $files) {
    $src = Join-Path $sharedDir $f
    if (-not (Test-Path $src)) {
        Write-Warning "File not found: $src"
        continue
    }
    $entryName = "extension/node_modules/@bytesized/shared/" + $f.Replace("\", "/")
    $existing = $zip.GetEntry($entryName)
    if ($existing) {
        $existing.Delete()
    }
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $src, $entryName) | Out-Null
    Write-Host "Injected $entryName into VSIX"
}

$zip.Dispose()
Write-Host "Successfully updated $vsixPath"
