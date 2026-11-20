# Install or update wwss for the current Windows user; configuration is untouched.
[CmdletBinding()]
param(
    [string]$Version = 'latest',
    [string]$ReleaseBaseUrl = 'https://github.com/gavsidhu/wwss/releases'
)

$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'This installer supports Windows. Use install.sh on Linux or macOS.'
}

# The registry records the native OS CPU, including in an emulated PowerShell.
$cpu = [Microsoft.Win32.Registry]::GetValue(
    'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'PROCESSOR_ARCHITECTURE', $null
)
if (-not $cpu) {
    $cpu = $env:PROCESSOR_ARCHITEW6432
    if (-not $cpu) { $cpu = $env:PROCESSOR_ARCHITECTURE }
}
switch ($cpu) {
    'AMD64' { $arch = 'amd64' }
    'ARM64' { $arch = 'arm64' }
    default { throw "Unsupported Windows architecture: $cpu. A 64-bit OS is required." }
}

$releaseRoot = $ReleaseBaseUrl.TrimEnd('/')
if ($Version -eq 'latest') {
    $manifestUrl = "$releaseRoot/latest/download/checksums.txt"
} else {
    $Version = $Version -replace '^v', ''
    if ($Version -notmatch '^[0-9][0-9A-Za-z.+-]*$') { throw 'Invalid release version' }
    $manifestUrl = "$releaseRoot/download/v$Version/checksums.txt"
}

# Windows PowerShell 5.1 may otherwise negotiate an older TLS protocol.
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$scratch = Join-Path ([IO.Path]::GetTempPath()) ("wwss-install-" + [Guid]::NewGuid().ToString('N'))
$stagedBinary = $null
New-Item -ItemType Directory -Path $scratch | Out-Null
try {
    Write-Host "Finding wwss for windows/$arch..."
    $manifestPath = Join-Path $scratch 'checksums.txt'
    Invoke-WebRequest -UseBasicParsing -Uri $manifestUrl -OutFile $manifestPath -TimeoutSec 120
    $suffix = "_windows_$arch.zip"
    $entries = @(foreach ($line in Get-Content -LiteralPath $manifestPath) {
        if ($line -match '^([0-9a-fA-F]{64})\s+(wwss_[0-9A-Za-z.+_-]+\.zip)$') {
            $entry = @{ Hash = $Matches[1]; Name = $Matches[2] }
            if ($entry.Name.EndsWith($suffix, [StringComparison]::Ordinal)) { $entry }
        }
    })
    if ($entries.Count -ne 1) { throw 'Missing or ambiguous archive in checksums.txt' }
    $asset = $entries[0].Name
    $assetVersion = $asset.Substring(5, $asset.Length - 5 - $suffix.Length)
    if ($assetVersion -notmatch '^[0-9][0-9A-Za-z.+-]*$') { throw 'Invalid archive version' }
    if ($Version -ne 'latest' -and $assetVersion -ne $Version) { throw 'Manifest version does not match requested release' }
    $archivePath = Join-Path $scratch $asset
    # Pin the archive URL to the manifest version to avoid a latest-release race.
    Invoke-WebRequest -UseBasicParsing -Uri "$releaseRoot/download/v$assetVersion/$asset" -OutFile $archivePath -TimeoutSec 300
    if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash -ne $entries[0].Hash) {
        throw 'Checksum mismatch; existing installation was not changed'
    }
    $payload = Join-Path $scratch 'payload'
    Expand-Archive -LiteralPath $archivePath -DestinationPath $payload
    foreach ($file in @('wwss.exe', 'LICENSE', 'README.md', 'docs\KNOWN_ISSUES.md', 'docs\RELEASING.md')) {
        if (-not (Test-Path -LiteralPath (Join-Path $payload $file) -PathType Leaf)) {
            throw "Archive is missing $file"
        }
    }
    & (Join-Path $payload 'wwss.exe') --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'The downloaded binary cannot run on this operating system' }

    if (-not $env:LOCALAPPDATA) { throw 'LOCALAPPDATA is not set' }
    $installDir = Join-Path $env:LOCALAPPDATA 'Programs\wwss'
    New-Item -ItemType Directory -Force -Path (Join-Path $installDir 'docs') | Out-Null
    $stagedBinary = Join-Path $installDir ('.wwss-' + [Guid]::NewGuid().ToString('N') + '.exe')
    Copy-Item -LiteralPath (Join-Path $payload 'wwss.exe') -Destination $stagedBinary
    foreach ($file in @('LICENSE', 'README.md')) {
        Copy-Item -LiteralPath (Join-Path $payload $file) -Destination (Join-Path $installDir $file) -Force
    }
    Copy-Item -Path (Join-Path $payload 'docs\*.md') -Destination (Join-Path $installDir 'docs') -Force
    $destination = Join-Path $installDir 'wwss.exe'
    if (Test-Path -LiteralPath $destination) {
        [IO.File]::Replace($stagedBinary, $destination, $null)
    } else {
        [IO.File]::Move($stagedBinary, $destination)
    }
    $stagedBinary = $null
    Set-Content -LiteralPath (Join-Path $installDir 'version.txt') -Value "v$assetVersion" -Encoding ASCII

    function Test-WwssPathEntry([string]$Value) {
        foreach ($part in ($Value -split ';')) {
            $normalized = [Environment]::ExpandEnvironmentVariables($part.Trim().Trim('"')).TrimEnd('\')
            if ($normalized -ieq $installDir.TrimEnd('\')) { return $true }
        }
        return $false
    }
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if (-not (Test-WwssPathEntry $userPath)) {
        $updatedPath = if ([string]::IsNullOrEmpty($userPath)) { $installDir } else { $userPath.TrimEnd(';') + ';' + $installDir }
        [Environment]::SetEnvironmentVariable('Path', $updatedPath, 'User')
    }
    if (-not (Test-WwssPathEntry $env:Path)) { $env:Path = $installDir + ';' + $env:Path }
    Write-Host "Installed wwss v$assetVersion at $destination"
    Write-Host 'Saved devices were preserved. Run: wwss --help'
} finally {
    if ($stagedBinary -and (Test-Path -LiteralPath $stagedBinary)) { Remove-Item -LiteralPath $stagedBinary -Force }
    Remove-Item -LiteralPath $scratch -Recurse -Force
}
