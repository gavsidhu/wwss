"""Check the native CLI in temporary homes, without sending wake packets."""

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import tempfile
import zipfile


def check_cli(binary, home):
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    config = home / ".wwss.json"

    def run(*args, input_text=None, succeeds=True):
        result = subprocess.run(
            [str(binary), *args], env=env, input=input_text,
            text=True, capture_output=True, timeout=15,
        )
        if (result.returncode == 0) != succeeds:
            raise AssertionError(f"{args}: {result.returncode}\n{result.stdout}\n{result.stderr}")
        return result

    run("--help")
    run("device", "list")
    if json.loads(config.read_text())["devices"]:
        raise AssertionError("Temporary configuration should start empty")
    for name, address, mac in [
        ("Office-PC", "192.0.2.20", "02:00:00:00:00:01"),
        ("other", "192.0.2.30", "02:00:00:00:00:02"),
    ]:
        run("device", "add", "--name", name, "--ipv4", address, "--mac", mac)
    original_other = json.loads(config.read_text())["devices"]["other"]
    run("device", "update", "OFFICE-PC", "--hostname", "office", "--ipv4", "192.0.2.21")
    devices = json.loads(config.read_text())["devices"]
    if devices["office-pc"]["hostname"] != "office" or devices["office-pc"]["local_ip_address"] != "192.0.2.21":
        raise AssertionError("Device update did not persist")
    listed = run("device", "list").stdout
    if "office-pc" not in listed or "other" not in listed:
        raise AssertionError("Saved devices missing from list")
    before = config.read_bytes()
    run("device", "update", "office-pc", "--ipv4", "invalid", succeeds=False)
    run("device", "add", "--name", "bad", "--ipv4", "192.0.2.40", "--mac", "invalid", succeeds=False)
    # An unknown device fails before any UDP packet is sent.
    run("wake", "missing-device", succeeds=False)
    run("device", "delete", "office-pc", input_text="no\n", succeeds=False)
    if config.read_bytes() != before:
        raise AssertionError("Failed or cancelled commands changed configuration")
    run("device", "delete", "office-pc", input_text="yes\n")
    if json.loads(config.read_text())["devices"] != {"other": original_other}:
        raise AssertionError("Delete did not preserve the other device")
    config.write_text("{invalid json", encoding="utf-8")
    run("device", "list", succeeds=False)
    if config.read_text() != "{invalid json":
        raise AssertionError("Malformed configuration was overwritten")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, help="Check a native binary from release archives")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="wwss-smoke-") as temporary:
        root = Path(temporary)
        home = root / "home"
        home.mkdir()
        executable = "wwss.exe" if os.name == "nt" else "wwss"
        binary = root / executable
        if args.dist:
            goos = {"Linux": "linux", "Darwin": "darwin", "Windows": "windows"}[platform.system()]
            arch = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}[platform.machine().lower()]
            extension = "zip" if goos == "windows" else "tar.gz"
            archives = list(args.dist.glob(f"wwss_*_{goos}_{arch}.{extension}"))
            if len(archives) != 1:
                raise AssertionError(f"Expected one native archive, found {archives}")
            if extension == "zip":
                with zipfile.ZipFile(archives[0]) as archive:
                    binary.write_bytes(archive.read(executable))
            else:
                with tarfile.open(archives[0]) as archive:
                    binary.write_bytes(archive.extractfile(executable).read())
            binary.chmod(0o755)
        else:
            repository = Path(__file__).resolve().parents[2]
            subprocess.run(
                ["go", "build", "-mod=readonly", "-trimpath", "-ldflags=-s -w", "-o", str(binary), "."],
                cwd=repository, env=dict(os.environ, CGO_ENABLED="0"), check=True, timeout=300,
            )
        check_cli(binary, home)
    print("CLI configuration checks passed; temporary homes used, no wake packets sent.")


if __name__ == "__main__":
    main()
