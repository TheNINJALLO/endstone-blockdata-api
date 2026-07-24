# Update from v0.4.0-alpha.4

1. Extract the v0.4.5-alpha.9 source ZIP.
2. Upload all files and folders to the root of the `endstone-blockdata-api` GitHub repository.
3. Allow GitHub to replace files with matching names.
4. Confirm that `.github/workflows/ci.yml`, `scripts/build_exact.sh`, and `scripts/build_exact.ps1` were replaced.
5. Commit the upload. A new **Build and Release** workflow starts automatically.
6. Do not create the `v0.4.5-alpha.9` tag until all four exact BDS jobs pass.

Linux no longer relies on the shell script executable bit. Windows now uses Visual Studio 2022/MSVC. If a build fails, download the new `*-diagnostics-*` artifact from the workflow run.
