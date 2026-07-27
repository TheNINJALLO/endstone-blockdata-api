# GitHub Actions builds and releases

The repository workflow is `.github/workflows/ci.yml`.

## Builds created on every push

Each push, pull request, or manual workflow run performs:

1. Portable C++ and Python tests on Ubuntu and Windows.
2. Exact native builds for BDS 1.26.33 / Endstone v0.11.6 on Linux x64 and Windows x64.
3. Installation into an isolated staging directory.
4. Creation of a raw plugin, self-contained platform wheel, complete ZIP package, package manifest, and SHA-256 file.
5. ELF/PE, archive, checksum, manifest, unresolved-Bedrock-symbol, and RPATH verification before upload.
6. Same-platform relocation/import smoke tests for each native bridge wheel, followed by cross-platform command and permission verification.

Open the workflow run in GitHub and download the desired item from the **Artifacts** section. Workflow artifacts are retained for 30 days.

## Automatic GitHub Release

Create and push a tag that exactly matches the version in `SOURCE_RELEASE.json`:

```bash
git tag v0.4.6
git push origin v0.4.6
```

The workflow downloads both verified exact-build artifacts, creates `SHA256SUMS.txt`, and publishes a normal stable GitHub Release. Because `v0.4.6` has no prerelease suffix, the workflow marks it as **Latest**, not as a prerelease.

Re-running the tagged workflow updates existing assets with `--clobber` rather than creating a duplicate release.

## Expected release assets

BDS 1.26.33 receives:

- A Windows x64 `.dll`
- A Linux x64 `.so`
- A Windows x64 ZIP package
- A Linux x64 ZIP package
- Per-package checksum files
- Verified Windows x64 and Linux x64 `endstone_blockdata_inspector` wheels
- A combined `SHA256SUMS.txt`

Each ZIP includes the native plugin and matching command wheel under `plugins/`, plus SDK headers, Python package, compatibility manifest, installation notes, and `PACKAGE_MANIFEST.json`.

## Important repository layout

Upload the contents of the repository folder to GitHub so `.github/workflows/ci.yml` is located at the repository root. GitHub will not discover the workflow if the entire repository is nested inside another directory.
