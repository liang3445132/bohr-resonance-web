$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $launcher = $null
    $launcherArgs = @()

    if (Get-Command py -ErrorAction SilentlyContinue) {
        $launcher = "py"
        $launcherArgs = @("-3")
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $launcher = "python"
    }
    else {
        $installed = Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Programs\Python\Python*\python.exe") `
            -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
        if ($installed) { $launcher = $installed.FullName }
    }

    if (-not $launcher) {
        throw "未找到 Python 3。请先安装 Python 3.10 或更高版本，并在安装时勾选 Add Python to PATH。"
    }

    & $launcher @launcherArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
}

& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$port = if ($env:PORT) { $env:PORT } else { "8501" }
& $python -m streamlit run app.py --server.address 0.0.0.0 --server.port $port --browser.gatherUsageStats false
exit $LASTEXITCODE
