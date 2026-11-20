# wwss

Save devices by name and send Wake-on-LAN magic packets from the command line.
The same CLI runs on Linux, macOS, and Windows. Release binaries include the Go
runtime; installing Go is only necessary when building from source.

## Download targets

Choose the archive for the operating system and CPU running **wwss**, rather than
the computer you want to wake. Download it and `checksums.txt` from the release.

| Machine | Archive suffix |
| --- | --- |
| Raspberry Pi 5 with 64-bit Ubuntu Server | `linux_arm64.tar.gz` |
| Linux x86-64 PC | `linux_amd64.tar.gz` |
| Apple Silicon Mac | `darwin_arm64.tar.gz` |
| Intel Mac | `darwin_amd64.tar.gz` |
| Windows x86-64 PC | `windows_amd64.zip` |
| Windows ARM64 PC | `windows_arm64.zip` |

Names have the form `wwss_0.1.0_linux_arm64.tar.gz`. Snapshot versions have an
additional suffix. Release builds use the Go version pinned in `.go-version`.
With the current toolchain, macOS 13 Ventura or later is required. See the
[Go platform requirements](https://go.dev/wiki/MinimumRequirements) for the other
runtime minimums. Native execution and real network delivery are separate checks;
see the [release checklist](docs/RELEASING.md).

## Install or update with one pasted command

These commands use public downloads from `gavsidhu/wwss`. They become live after
its first published, non-prerelease GitHub release includes the installers.
No Go installation or administrator access is required. The installer selects
ARM64 or x86-64, verifies the archive's SHA-256 checksum, and preserves saved
configuration. Run the same command again to update.

### Linux and macOS (bash or zsh)

```sh
wwss_setup=$(mktemp) && curl -fsSL https://github.com/gavsidhu/wwss/releases/latest/download/install.sh -o "$wwss_setup" && sh "$wwss_setup" && rm -f "$wwss_setup" && export PATH="$HOME/.local/bin:$PATH"
```

This installs `~/.local/bin/wwss`, adds that directory to the appropriate shell
startup files for future terminals, and makes it available in the current
terminal. License texts, documentation, and `version.txt` are stored in
`~/.local/share/wwss`. Standard `curl`, `tar`, and a SHA-256 utility are required;
macOS and typical Ubuntu Server installations provide the other shell tools.

### Windows PowerShell

```powershell
& ([scriptblock]::Create((New-Object Net.WebClient).DownloadString('https://github.com/gavsidhu/wwss/releases/latest/download/install.ps1')))
```

### Windows Command Prompt (CMD)

```bat
powershell -NoProfile -Command "& ([scriptblock]::Create((New-Object Net.WebClient).DownloadString('https://github.com/gavsidhu/wwss/releases/latest/download/install.ps1')))" && set "PATH=%LOCALAPPDATA%\Programs\wwss;%PATH%"
```

Windows installs `wwss.exe` and its documentation under
`%LOCALAPPDATA%\Programs\wwss`, adds that directory to your user PATH, and
updates the current PowerShell process. The CMD command also updates its parent
CMD window. Existing terminal windows other than the one running the command
may need to be reopened.

After installation, run:

```sh
wwss --help
```

You can inspect [install.sh](install.sh) or [install.ps1](install.ps1) before
running it. For a specific release, download its installer and run
`sh install.sh --version v0.1.0` or `& .\install.ps1 -Version v0.1.0`.
Testing releases use their full tag, such as `v0.1.0-rc.1`.

Initial executables are not Developer ID signed/notarized on macOS or
Authenticode signed on Windows. If the OS asks you to approve the executable,
use its normal approval flow for the verified download.

## Use

```sh
wwss device add --name office-pc --ipv4 192.168.1.20 --mac aa:bb:cc:dd:ee:ff
wwss device list
wwss device update office-pc --ipv4 192.168.1.30
wwss wake office-pc
wwss device delete office-pc
```

Device names are case insensitive. Use simple names such as `office-pc`; dotted
names currently have a [known persistence issue](docs/KNOWN_ISSUES.md).
`device add` and `device update` also accept `--hostname` and `--tailscale-ip`.
Those fields are stored as metadata; `wake` uses the saved local IPv4 and MAC.

The sender must be able to broadcast onto the target device's LAN. Enable
Wake-on-LAN in the target's firmware and network adapter settings. The command
sends an IPv4 UDP magic packet to port 9 and prints `Magic packet sent` after a
successful send; it does not check whether the device actually woke.

### Raspberry Pi over SSH or Tailscale

Confirm the Pi's Ubuntu version and architecture:

```sh
cat /etc/os-release
uname -m
```

For `aarch64`, install the Linux ARM64 archive on the Pi. Then run commands as
your regular Ubuntu user, including from another computer:

```sh
ssh user@pi '"$HOME/.local/bin/wwss" wake office-pc'
```

Use the Pi's Tailscale hostname or IP in place of `pi` for access over Tailscale.
The command executes on the Pi and sends the packet on its local network.

## Configuration and updates

wwss creates a JSON configuration on the first command that needs it:

- Linux and macOS: `~/.wwss.json`
- Windows: `%USERPROFILE%\.wwss.json`

Back up that file before changing devices. Avoid overlapping add, update, and
delete commands while the documented concurrency issue remains open.

To update, rerun the installation command. A failed download or checksum check
leaves the existing executable in place. Saved devices remain in the user's
configuration file. The CLI currently has no `--version` flag; the installer
records the installed release in `version.txt` beside its documentation.

To remove the application on Linux/macOS, delete `~/.local/bin/wwss` and
`~/.local/share/wwss`. On Windows, remove `%LOCALAPPDATA%\Programs\wwss` and
its user PATH entry. The Unix PATH block is marked `wwss PATH` in the relevant
startup files and may be removed if no longer needed. Remove `.wwss.json`
separately if you also want to delete saved devices.

## Build from source

The module requires Go 1.24.4 or newer. CI and release builds use `.go-version`.

```sh
go test -mod=readonly ./...
go build -mod=readonly -trimpath -o wwss .
```

On Windows, use `-o wwss.exe`. See [RELEASING.md](docs/RELEASING.md) for the
cross-platform packaging workflow and [KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) for
deferred application changes.

## License

[MIT](LICENSE). Bundled dependency and Go runtime license texts are included in
[THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES).
