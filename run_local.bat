@echo off
setlocal
set "OOP_LAUNCHER_FILE=%~f0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -Command "$code = ([IO.File]::ReadAllText($env:OOP_LAUNCHER_FILE) -split '(?m)^# POWERSHELL START\r?$', 2)[1]; & ([scriptblock]::Create($code))"
set "launcher_exit=%errorlevel%"
if not "%launcher_exit%"=="0" pause
exit /b %launcher_exit%
# POWERSHELL START
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$env:PIP_CONFIG_FILE = 'nul'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
[Reflection.Assembly]::LoadWithPartialName('System.IO.Compression.FileSystem') | Out-Null

try {
    if (-not [Environment]::Is64BitOperatingSystem) {
        throw 'This launcher requires Windows 10 or 11 (64-bit).'
    }

    $revision = '84b1f413631ffba8e45b014a4f7726568b0185fc'
    $cacheBase = Join-Path $env:LOCALAPPDATA 'OOPTeamProjectLocal'
    if ($env:OOP_LOCAL_HOME) { $cacheBase = $env:OOP_LOCAL_HOME }
    $cache = Join-Path $cacheBase '84b1f41-python3146'
    New-Item -ItemType Directory -Path $cache -Force | Out-Null

    function Download-File($url, $destination) {
        if (-not (Test-Path -LiteralPath $destination)) {
            Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile "$destination.part" -TimeoutSec 180
            Move-Item -LiteralPath "$destination.part" -Destination $destination -Force
        }
    }

    function Expand-Zip($archivePath, $destination) {
        $root = [IO.Path]::GetFullPath($destination).TrimEnd('\') + '\'
        $archive = [IO.Compression.ZipFile]::OpenRead($archivePath)
        try {
            foreach ($entry in $archive.Entries) {
                $target = [IO.Path]::GetFullPath((Join-Path $root $entry.FullName))
                if (-not $target.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
                    throw 'The downloaded archive contains an invalid path.'
                }
                if ($entry.FullName.EndsWith('/')) {
                    [IO.Directory]::CreateDirectory($target) | Out-Null
                }
                else {
                    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
                    $source = $entry.Open()
                    $output = [IO.File]::Create($target)
                    try { $source.CopyTo($output) }
                    finally { $source.Dispose(); $output.Dispose() }
                }
            }
        }
        finally { $archive.Dispose() }
    }

    $pythonHome = Join-Path $cache 'python'
    $python = Join-Path $pythonHome 'python.exe'
    if (-not (Test-Path -LiteralPath (Join-Path $pythonHome 'runtime.ready'))) {
        Write-Host '[1/4] Downloading a private Python runtime...'
        $pythonZip = Join-Path $cache 'python-3.14.6.zip'
        Download-File 'https://www.python.org/ftp/python/3.14.6/python-3.14.6-embed-amd64.zip' $pythonZip
        $expectedHash = 'df901e84a896ff1ee720ad03377e0c8d8c2244fda79808aeeaff6316df1cb75c'
        $hasher = [Security.Cryptography.SHA256]::Create()
        $archiveStream = [IO.File]::OpenRead($pythonZip)
        try { $actualHash = [BitConverter]::ToString($hasher.ComputeHash($archiveStream)).Replace('-', '').ToLowerInvariant() }
        finally { $archiveStream.Dispose(); $hasher.Dispose() }
        if ($actualHash -ne $expectedHash) {
            Remove-Item -LiteralPath $pythonZip -Force
            throw 'The Python download did not match its published checksum. Download was not run.'
        }
        try { Expand-Zip $pythonZip $pythonHome }
        catch { Remove-Item -LiteralPath $pythonZip -Force; throw }
        Set-Content -LiteralPath (Join-Path $pythonHome 'python314._pth') -Encoding ASCII -Value @(
            'python314.zip', '.', 'Lib\site-packages', 'import site'
        )
        & $python -I -c 'import ssl, sys; print(sys.version)'
        if ($LASTEXITCODE -ne 0) { throw 'The downloaded Python runtime could not start.' }
        Set-Content -LiteralPath (Join-Path $pythonHome 'runtime.ready') -Value 'ready'
    }

    $project = Join-Path $cache "OOPTeamProject-$revision"
    if (-not (Test-Path -LiteralPath (Join-Path $cache 'project.ready'))) {
        Write-Host '[2/4] Downloading the project and CSV archive...'
        $projectZip = Join-Path $cache 'project.zip'
        Download-File "https://codeload.github.com/Noaheo/OOPTeamProject/zip/$revision" $projectZip
        try { Expand-Zip $projectZip $cache }
        catch { Remove-Item -LiteralPath $projectZip -Force; throw }
        foreach ($file in @('app.py', 'requirements.txt', 'data(23~25).zip')) {
            if (-not (Test-Path -LiteralPath (Join-Path $project $file))) {
                throw "The project download is incomplete: $file is missing."
            }
        }
        Set-Content -LiteralPath (Join-Path $cache 'project.ready') -Value 'ready'
    }

    $dataFolder = Join-Path $project 'data'
    $dataArchivePath = Join-Path $project 'data(23~25).zip'
    $dataArchive = [IO.Compression.ZipFile]::OpenRead($dataArchivePath)
    $dataComplete = $true
    try {
        foreach ($entry in $dataArchive.Entries) {
            if ($entry.FullName.EndsWith('.csv')) {
                $csv = [IO.FileInfo]::new((Join-Path $dataFolder $entry.FullName))
                if (-not $csv.Exists -or $csv.Length -ne $entry.Length) {
                    $dataComplete = $false
                    break
                }
            }
        }
    }
    finally { $dataArchive.Dispose() }
    if (-not $dataComplete) {
        Write-Host '[2/4] Preparing the local CSV files...'
        Expand-Zip $dataArchivePath $dataFolder
    }

    if (-not (Test-Path -LiteralPath (Join-Path $cache 'packages.ready'))) {
        Write-Host '[3/4] Installing libraries for this app only. This may take a few minutes...'
        if (-not (Test-Path -LiteralPath (Join-Path $pythonHome 'Lib\site-packages\pip\__init__.py'))) {
            $getPip = Join-Path $cache 'get-pip.py'
            Download-File 'https://bootstrap.pypa.io/get-pip.py' $getPip
            & $python -I $getPip --isolated --no-input --no-warn-script-location --disable-pip-version-check
            if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the package installer. Check the internet connection and retry.' }
        }
        & $python -I -m pip --isolated install --no-input --disable-pip-version-check --no-warn-script-location --only-binary=:all: -r (Join-Path $project 'requirements.txt') 'streamlit==1.66.1' 'pandas==3.1.0' 'plotly==7.1.0'
        if ($LASTEXITCODE -ne 0) { throw 'Could not download the required libraries. Check the internet connection and retry.' }
        & $python -I -c 'import streamlit, pandas, plotly, pyarrow'
        if ($LASTEXITCODE -ne 0) { throw 'The required libraries could not be loaded.' }
        Set-Content -LiteralPath (Join-Path $cache 'packages.ready') -Value 'ready'
    }

    $port = 8501
    while ($port -le 8520) {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $port)
        try { $listener.Start(); $listener.Stop(); break }
        catch { $listener.Stop(); $port++ }
    }
    if ($port -gt 8520) { throw 'No local port is available between 8501 and 8520.' }

    Write-Host "[4/4] Opening http://127.0.0.1:$port"
    Write-Host 'Keep this window open. Press Ctrl+C to stop the dashboard.'
    $headless = 'false'
    if ($env:OOP_LOCAL_HEADLESS -eq '1') { $headless = 'true' }
    Push-Location -LiteralPath $project
    try {
        & $python -I -m streamlit run app.py "--server.port=$port" '--server.address=127.0.0.1' '--browser.serverAddress=127.0.0.1' "--browser.serverPort=$port" "--server.headless=$headless" '--server.showEmailPrompt=false' '--browser.gatherUsageStats=false' '--server.fileWatcherType=none'
        $serverExit = $LASTEXITCODE
    }
    finally { Pop-Location }
    exit $serverExit
}
catch {
    Write-Host ''
    Write-Host "Could not start the dashboard: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'The first setup needs internet access to python.org, pypi.org and github.com.'
    exit 1
}
