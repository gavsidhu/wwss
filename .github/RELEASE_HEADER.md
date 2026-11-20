Native binaries for Linux, macOS, and Windows on ARM64 and x86-64.
Verify your archive against `checksums.txt` before installing.

The following configuration issues remain open in this release:

- Failed configuration writes can truncate the previous file and lose saved devices.
- Overlapping device changes can overwrite each other, including while delete waits for confirmation.
- Dotted names can create extra, incomplete device records.

Back up `.wwss.json` before changing devices, run one device mutation at a time,
and use simple names such as `office-pc`. Full details and reproduction examples
are in `docs/KNOWN_ISSUES.md` inside every archive.

