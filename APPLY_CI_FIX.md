# Required GitHub workflow replacement

The failed jobs named `Portable tests (ubuntu-22.04)` are from the old workflow.
This release uses jobs named `Portable tests v0.4.5 (ubuntu-24.04)`.

Uploading ordinary visible files is not enough if `.github/workflows/ci.yml` is not replaced.

## Reliable browser method

1. Open the repository on GitHub.
2. Open `.github/workflows/ci.yml`.
3. Click the pencil icon to edit it.
4. Replace the entire file with the contents of `CI_WORKFLOW_COPY.yml` from this package.
5. Commit directly to `main`.
6. Confirm the new Actions run contains `Portable tests v0.4.5 (ubuntu-24.04)`.

The workflow calls `python scripts/build_exact.py`, not `./scripts/build_exact.sh`, so Linux file permissions cannot produce exit code 126.

## Files that must also be uploaded

- `scripts/build_exact.py`
- `scripts/build_exact.sh`
- `scripts/build_exact.ps1`
- `SOURCE_RELEASE.json`
- `CI_WORKFLOW_COPY.yml`

Do not create tag `v0.4.5-alpha.9` until all exact jobs pass.
