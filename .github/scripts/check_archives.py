"""Verify the six release archives, binary targets, bundled docs, and checksums."""

import argparse
import hashlib
from pathlib import Path
import struct
import tarfile
import zipfile


REQUIRED_FILES = {
    "LICENSE", "README.md",
    "docs/KNOWN_ISSUES.md", "docs/RELEASING.md",
}
INSTALLERS = {"install.sh", "install.ps1"}


def check_binary(data, goos, arch):
    if goos == "linux":
        if data[:6] != b"\x7fELF\x02\x01":
            raise AssertionError("Expected a 64-bit little-endian ELF binary")
        machine = struct.unpack_from("<H", data, 18)[0]
        expected = {"amd64": 62, "arm64": 183}[arch]
    elif goos == "windows":
        if data[:2] != b"MZ":
            raise AssertionError("Expected a Windows executable")
        pe = struct.unpack_from("<I", data, 60)[0]
        if data[pe:pe + 4] != b"PE\0\0":
            raise AssertionError("Missing PE header")
        machine = struct.unpack_from("<H", data, pe + 4)[0]
        expected = {"amd64": 0x8664, "arm64": 0xAA64}[arch]
    else:
        if data[:4] != b"\xcf\xfa\xed\xfe":
            raise AssertionError("Expected a 64-bit little-endian Mach-O binary")
        machine = struct.unpack_from("<I", data, 4)[0]
        expected = {"amd64": 0x01000007, "arm64": 0x0100000C}[arch]
    if machine != expected:
        raise AssertionError(f"Wrong CPU for {goos}/{arch}: {machine:#x}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    args = parser.parse_args()
    checksums = {}
    for line in (args.dist / "checksums.txt").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        if name in checksums or Path(name).name != name:
            raise AssertionError(f"Invalid checksum filename: {name}")
        checksums[name] = digest.lower()
    archives = sorted([*args.dist.glob("*.tar.gz"), *args.dist.glob("*.zip")])
    if len(archives) != 6 or set(checksums) != {path.name for path in archives} | INSTALLERS:
        raise AssertionError("Expected exactly six archives and both installers covered by checksums")
    for name in INSTALLERS:
        content = (args.dist / name).read_bytes()
        if not content or hashlib.sha256(content).hexdigest() != checksums[name]:
            raise AssertionError(f"Missing installer or checksum mismatch: {name}")
    targets = set()
    versions = set()
    for path in archives:
        extension = ".zip" if path.suffix == ".zip" else ".tar.gz"
        stem = path.name.removesuffix(extension)
        project_version, goos, arch = stem.rsplit("_", 2)
        if not project_version.startswith("wwss_") or goos not in {"linux", "darwin", "windows"} or arch not in {"amd64", "arm64"}:
            raise AssertionError(f"Unexpected archive name: {path.name}")
        if extension != (".zip" if goos == "windows" else ".tar.gz"):
            raise AssertionError(f"Wrong archive format for {goos}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != checksums[path.name]:
            raise AssertionError(f"Checksum mismatch: {path.name}")
        executable = "wwss.exe" if goos == "windows" else "wwss"
        expected = REQUIRED_FILES | {executable}
        if extension == ".zip":
            with zipfile.ZipFile(path) as archive:
                files = {item.filename for item in archive.infolist() if not item.is_dir()}
                contents = {name: archive.read(name) for name in files}
        else:
            with tarfile.open(path) as archive:
                files = {item.name for item in archive.getmembers() if item.isfile()}
                contents = {name: archive.extractfile(name).read() for name in files}
                if not archive.getmember(executable).mode & 0o111:
                    raise AssertionError(f"Missing executable permission: {path.name}")
        if files != expected or any(not content for content in contents.values()):
            raise AssertionError(f"Missing, extra, or empty archive contents: {path.name}: {files}")
        check_binary(contents[executable], goos, arch)
        targets.add((goos, arch))
        versions.add(project_version)
        print(f"Verified {path.name}")
    if len(targets) != 6 or len(versions) != 1:
        raise AssertionError("Expected one version and all six OS/CPU pairs")


if __name__ == "__main__":
    main()
