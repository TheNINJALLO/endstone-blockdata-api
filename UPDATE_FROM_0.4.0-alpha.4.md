# Update from v0.4.0-alpha.4

1. Extract the v0.4.5-beta.30 source ZIP.
2. Upload all files and folders to the root of the `endstone-blockdata-api` GitHub repository.
3. Allow GitHub to replace files with matching names.
4. Confirm that `.github/workflows/ci.yml`, `scripts/build_exact.sh`, and `scripts/build_exact.ps1` were replaced.
5. Commit the upload. A new **Build and Release** workflow starts automatically.
6. Do not create the `v0.4.5-beta.30` tag until both BDS 1.26.33 exact jobs and the command-test wheel job pass.

Both platforms run `scripts/build_exact.py`. Linux uses Clang 18/libc++ and Windows uses clang-cl/lld-link/Ninja inside the Visual Studio 2022 environment. If a build fails, download the new `*-diagnostics-*` artifact from the workflow run.
