param(
  [ValidateSet("1.26.32", "1.26.33")][string]$BdsBuild = "1.26.33",
  [ValidateSet("windows-x64")][string]$Platform = "windows-x64"
)
$ErrorActionPreference = "Stop"
python scripts/build_exact.py --bds $BdsBuild --platform $Platform
if ($LASTEXITCODE -ne 0) { throw "Exact build failed with exit code $LASTEXITCODE" }
