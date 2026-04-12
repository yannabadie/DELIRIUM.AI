$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir))

$repoRootWsl = (wsl.exe -d coral-ubuntu -- bash -lc "wslpath -a '$repoRoot'").Trim()
if (-not $repoRootWsl) {
    throw "Unable to translate repo path to WSL."
}

$linuxCommand = @"
cd '$repoRootWsl'
bash orchestration/coral/scripts/run_delirium_coral.sh
"@

wsl.exe -d coral-ubuntu -- bash -lc $linuxCommand
