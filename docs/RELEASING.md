# Releasing wwss

## Tooling and files

- `.go-version` pins the release toolchain separately from the minimum in `go.mod`.
- `.goreleaser.yaml` builds all six OS/CPU pairs with `CGO_ENABLED=0`.
- CI runs tests, vet, and CLI configuration checks on Linux, macOS, and Windows.
- Installer integration checks use a local fixture server to verify installs,
  updates, PATH setup, and failure handling while preserving saved configuration.
- CI also packages all six targets, verifies archive contents and SHA-256 sums,
  and checks the native executable extracted from an archive.
- Tag pushes run those same checks before creating a **draft** GitHub release.

Use GoReleaser v2.20.3 (the version pinned in both workflows). A v1 installation
cannot validate this v2 configuration. No application version symbols or new CLI
flags are required by the release build.

## Local packaging

GoReleaser needs a Git commit and a repository remote, including for snapshot
metadata. The initial repository must be committed and connected to its intended
GitHub repository before using these commands in the working checkout.

```sh
goreleaser check
go test -mod=readonly ./...
go vet -mod=readonly ./...
python3 .github/scripts/smoke_cli.py
python3 .github/scripts/test_installers.py
goreleaser release --snapshot --clean
python3 -c "import shutil; shutil.copy2('install.sh', 'dist/install.sh'); shutil.copy2('install.ps1', 'dist/install.ps1')"
python3 .github/scripts/check_archives.py dist
python3 .github/scripts/smoke_cli.py --dist dist
```

Use the Go version from `.go-version` for the commands above. On Windows use
`python` if `python3` is not available. Snapshot archives are local artifacts and
are not published. `--clean` removes the previous `dist` output.

The scripts use temporary directories and temporary child-process home
directories. They do not edit your saved devices or send Wake-on-LAN packets.
The Windows installer test restores the test user's original registry PATH
after checking persistence. Run it in CI or a disposable Windows account.

## Before the first release

- [ ] Create the intended GitHub repository, set its visibility, connect the
      remote, and commit the reviewed project files.
- [ ] Use a public repository and published release for the anonymous installer
      links in README. Confirm the intended repository is `gavsidhu/wwss` or
      update both installers and the README commands to the chosen destination.
- [ ] Push the branch and wait for CI to pass on all three operating systems.
- [ ] Confirm the Pi's Ubuntu Server version and that `uname -m` reports
      `aarch64` for the ARM64 binary.
- [ ] Verify the installation, configuration, update, and removal instructions
      on Linux, macOS, and Windows.
- [ ] Verify both Windows PowerShell and CMD commands expose `wwss` immediately,
      and new bash/zsh terminals can find it after installation.
- [ ] Test actual wake delivery on each OS, including the Pi with Tailscale
      active and the network interfaces normally used there.
- [ ] Test restoring the backed-up config and previous binary.
- [ ] Review the deferred issues in `KNOWN_ISSUES.md` and retain them in the
      release notes if shipping the current behavior.
- [ ] Review dependency license texts in `THIRD_PARTY_NOTICES`. Refresh the
      applicable texts when dependencies or the Go toolchain change.

Build success and hosted-runner tests do not verify Wake-on-LAN delivery to real
hardware. Record the OS versions, architectures, and hardware results in the
draft's release notes before publishing. The current Go 1.27 toolchain requires
macOS 13 or later; its [release notes](https://go.dev/doc/go1.27#ports) document
that runtime minimum.

## Create the draft

Once the reviewed changes are committed and CI passes, choose the version and
push an annotated tag, for example:

```sh
git tag -a v0.1.0 -m "wwss v0.1.0"
git push origin v0.1.0
```

The release workflow first runs the reusable CI workflow, then builds versioned
archives without publishing. It verifies those archives and checks the packaged
native CLI before uploading them to a draft release. GitHub's built-in
`GITHUB_TOKEN` supplies the repository-scoped permission; no personal token is
needed for releases in the same repository.

The workflow prepends `.github/RELEASE_HEADER.md` to GoReleaser's generated
changelog so the three deferred configuration issues appear in the draft notes.

Open the draft under the repository's Releases tab, review the notes and assets,
download and verify the archives, and publish when the checklist is complete.
For a testing release, use a tag such as `v0.1.0-rc.1`; the workflow marks tags
with a prerelease suffix as prereleases. Creating a draft does not change
repository visibility.

## Release assets

Each archive contains `wwss` or `wwss.exe`, `README.md`, `LICENSE`,
`THIRD_PARTY_NOTICES`, and the known-issues and release documents. A separate
`checksums.txt` covers all six archives and the separately uploaded `install.sh`
and `install.ps1`. The installers use the latest release's checksum manifest,
then pin the archive download to that manifest's version. Native signatures and macOS
notarization are not configured for the initial release.

The `releases/latest/download` installer commands need a published, non-prerelease
release. Drafts and testing releases are installed by downloading the desired
tag's installer and passing its explicit version. Checksums detect damaged or
mismatched assets; they do not replace publisher signatures.

The CLI does not expose an application version. Keep the versioned archive name
with installation records. Adding `--version` or `--config`, or fixing the three
configuration issues, would require application changes and remains separate work.
