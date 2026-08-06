param(
  [ValidateSet("1.26.40")][string]$BdsBuild = "1.26.40",
  [ValidateSet("windows-x64")][string]$Platform = "windows-x64"
)
$ErrorActionPreference = "Stop"
python scripts/build_exact.py --bds $BdsBuild --platform $Platform
if ($LASTEXITCODE -ne 0) { throw "Exact build failed with exit code $LASTEXITCODE" }
