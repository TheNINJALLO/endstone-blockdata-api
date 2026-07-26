# GitHub Actions builds and releases

The repository workflow is `.github/workflows/ci.yml`.

## Builds created on every push

Each push, pull request, or manual workflow run performs:

1. Portable C++ and Python tests on Ubuntu and Windows.
2. Exact native builds for BDS 1.26.33 / Endstone v0.11.6 on Linux x64 and Windows x64.
3. Installation into an isolated staging directory.
4. Creation of a raw plugin, complete ZIP package, package manifest, and SHA-256 file.
5. ELF/PE, archive, checksum, manifest, unresolved-Bedrock-symbol, and RPATH verification before upload.
6. One clean build of the Python command-test wheel, followed by real Endstone command and permission construction tests.

Open the workflow run in GitHub and download the desired item from the **Artifacts** section. Workflow artifacts are retained for 30 days.

## Automatic GitHub Release

Create and push a tag that exactly matches the version in `SOURCE_RELEASE.json`:

```bash
git tag v0.4.5-beta.29
git push origin v0.4.5-beta.29
```

The workflow downloads both exact-build artifacts and the verified test wheel, creates `SHA256SUMS.txt`, and creates a GitHub Release. Because this version contains a hyphen, GitHub marks it as a prerelease rather than incorrectly making it the latest stable release.

Re-running the tagged workflow updates existing assets with `--clobber` rather than creating a duplicate release.

## Expected release assets

BDS 1.26.33 receives:

- A Windows x64 `.dll`
- A Linux x64 `.so`
- A Windows x64 ZIP package
- A Linux x64 ZIP package
- Per-package checksum files
- The verified `endstone_blockdata_inspector` command-test wheel
- A combined `SHA256SUMS.txt`

The ZIP includes the plugin, SDK headers, Python package where applicable, compatibility manifest, installation notes, and `PACKAGE_MANIFEST.json`.

## Important repository layout

Upload the contents of the repository folder to GitHub so `.github/workflows/ci.yml` is located at the repository root. GitHub will not discover the workflow if the entire repository is nested inside another directory.
