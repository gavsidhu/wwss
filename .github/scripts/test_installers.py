"""Exercise install/update, PATH setup, and failure handling against local fixtures."""

import functools
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import threading
import zipfile


REPOSITORY = Path(__file__).resolve().parents[2]
DOCS = ["LICENSE", "README.md", "docs/KNOWN_ISSUES.md", "docs/RELEASING.md"]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    windows = os.name == "nt"
    saved_user_path = None
    registry = None
    if windows:
        import winreg
        registry = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment")
        try:
            saved_user_path = winreg.QueryValueEx(registry, "Path")
        except FileNotFoundError:
            pass
    try:
        with tempfile.TemporaryDirectory(prefix="wwss installer tests ") as temporary:
            root = Path(temporary)
            native = root / ("wwss.exe" if windows else "wwss")
            subprocess.run(
                ["go", "build", "-mod=readonly", "-o", str(native), "."], cwd=REPOSITORY,
                env=dict(os.environ, CGO_ENABLED="0"), check=True, timeout=300,
            )
            fixture = root / "releases"
            for version in ["1.0.0", "2.0.0", "3.0.0", "4.0.0", "5.0.0"]:
                release = fixture / "download" / ("v" + version)
                release.mkdir(parents=True)
                lines = []
                for goos in ["linux", "darwin", "windows"]:
                    for arch in ["amd64", "arm64"]:
                        filename = f"wwss_{version}_{goos}_{arch}." + ("zip" if goos == "windows" else "tar.gz")
                        files = {name: (REPOSITORY / name).read_bytes() for name in DOCS}
                        files["README.md"] += f"\nInstaller fixture: {goos}/{arch}\n".encode()
                        files["wwss.exe" if goos == "windows" else "wwss"] = native.read_bytes()
                        archive = release / filename
                        if goos == "windows":
                            with zipfile.ZipFile(archive, "w") as output:
                                for name, data in files.items():
                                    output.writestr(name, data)
                        else:
                            with tarfile.open(archive, "w:gz") as output:
                                for name, data in files.items():
                                    info = tarfile.TarInfo(name)
                                    info.size = len(data)
                                    info.mode = 0o755 if name == "wwss" else 0o644
                                    output.addfile(info, io.BytesIO(data))
                        digest = "0" * 64 if version == "3.0.0" else hashlib.sha256(archive.read_bytes()).hexdigest()
                        lines.append(f"{digest}  {filename}\n")
                        if version == "4.0.0":
                            archive.unlink()
                if version == "5.0.0":
                    lines *= 2
                (release / "checksums.txt").write_text("".join(lines))
            latest = fixture / "latest" / "download"
            latest.mkdir(parents=True)
            shutil.copyfile(fixture / "download/v2.0.0/checksums.txt", latest / "checksums.txt")
            shutil.copyfile(REPOSITORY / "install.ps1", latest / "install.ps1")
            shutil.copyfile(REPOSITORY / "install.sh", latest / "install.sh")
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(root)))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base_url = f"http://127.0.0.1:{server.server_port}/releases"
            try:
                home = root / "test home"
                home.mkdir()
                config = home / ".wwss.json"
                config.write_text(json.dumps({"devices": {"keep-me": {"mac_address": "02:00:00:00:00:01"}}}))
                original_config = config.read_bytes()
                env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), LOCALAPPDATA=str(home / "AppData/Local"), SHELL="/bin/bash", WWSS_RELEASE_BASE_URL=base_url)
                if windows:
                    # CI's PowerShell 7 module paths are incompatible with the
                    # Windows PowerShell 5.1 children launched through Python/CMD.
                    # Let powershell.exe construct its native module search path.
                    env = {key: value for key, value in env.items() if key.upper() != "PSMODULEPATH"}
                install_dir = Path(env["LOCALAPPDATA"]) / "Programs/wwss" if windows else home / ".local/bin"
                data_dir = install_dir if windows else home / ".local/share/wwss"
                executable = install_dir / ("wwss.exe" if windows else "wwss")

                def install(version=None, succeeds=True, custom_env=None):
                    use_env = dict(env if custom_env is None else custom_env)
                    if windows:
                        use_env.update(WWSS_TEST_SCRIPT=str(REPOSITORY / "install.ps1"), WWSS_TEST_BASE=base_url, WWSS_TEST_VERSION=version or "latest")
                        code = (
                            "$ErrorActionPreference='Stop'; "
                            "& ([scriptblock]::Create((Get-Content -Raw -LiteralPath $env:WWSS_TEST_SCRIPT))) "
                            "-ReleaseBaseUrl $env:WWSS_TEST_BASE -Version $env:WWSS_TEST_VERSION; "
                            "& wwss --help | Out-Null; if ($LASTEXITCODE -ne 0) { throw 'PATH did not expose wwss' }"
                        )
                        command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", code]
                    else:
                        command = ["sh", str(REPOSITORY / "install.sh")]
                        if version:
                            command += ["--version", version]
                    result = subprocess.run(command, env=use_env, text=True, capture_output=True, timeout=60)
                    if (result.returncode == 0) != succeeds:
                        raise AssertionError(f"Install {version}: {result.returncode}\n{result.stdout}\n{result.stderr}")
                    return result

                install("v1.0.0")
                assert executable.is_file()
                assert (data_dir / "version.txt").read_text().strip() == "v1.0.0"
                install()  # latest resolves the manifest, then downloads that exact version.
                install("2.0.0")  # Repeat installation must keep PATH entries idempotent.
                assert (data_dir / "version.txt").read_text().strip() == "v2.0.0"
                assert config.read_bytes() == original_config
                installed_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
                for bad_version in ["3.0.0", "4.0.0", "5.0.0", "../invalid"]:
                    install(bad_version, succeeds=False)
                    assert hashlib.sha256(executable.read_bytes()).hexdigest() == installed_hash
                    assert (data_dir / "version.txt").read_text().strip() == "v2.0.0"
                    assert config.read_bytes() == original_config
                for name in DOCS:
                    assert (data_dir / name).is_file()
                if windows:
                    import winreg
                    updated, _ = winreg.QueryValueEx(registry, "Path")
                    assert sum(part.rstrip("\\").lower() == str(install_dir).lower() for part in updated.split(";")) == 1
                    # Start fresh: a previous PowerShell install must not mask a
                    # bootstrap that prints its command instead of running it.
                    cmd_home = root / "cmd test home"
                    cmd_home.mkdir()
                    cmd_config = cmd_home / ".wwss.json"
                    cmd_config.write_bytes(original_config)
                    resolved = root / "cmd resolved executable.txt"
                    cmd_env = dict(env, HOME=str(cmd_home), USERPROFILE=str(cmd_home),
                                   LOCALAPPDATA=str(cmd_home / "AppData/Local"), WWSS_TEST_RESOLVED=str(resolved))
                    cmd_install_dir = Path(cmd_env["LOCALAPPDATA"]) / "Programs/wwss"
                    cmd_executable = cmd_install_dir / "wwss.exe"
                    cmd_script = root / "install from cmd.cmd"

                    def install_from_cmd(version=None, succeeds=True):
                        command = (
                            'powershell.exe -NoProfile -Command "& ([scriptblock]::Create((New-Object Net.WebClient).DownloadString(\''
                            + base_url + '/latest/download/install.ps1\'))) -ReleaseBaseUrl \'' + base_url + "'"
                            + (f" -Version '{version}'" if version else "") + '"'
                            + ' && set "PATH=%LOCALAPPDATA%\\Programs\\wwss;%PATH%" && wwss --help'
                        )
                        # Keep the pasted command out of subprocess's C-runtime
                        # quoting. CMD reads its quotes literally from this file.
                        cmd_script.write_bytes((
                            "@echo off\r\n" + command + "\r\n"
                            "if errorlevel 1 exit /b %errorlevel%\r\n"
                            'where.exe wwss > "%WWSS_TEST_RESOLVED%"\r\n'
                            "exit /b %errorlevel%\r\n"
                        ).encode("ascii"))
                        resolved.unlink(missing_ok=True)
                        cmd_exe = cmd_env.get("COMSPEC", "cmd.exe")
                        # /s strips the outer quotes, leaving the script's path
                        # quoted even when its temporary directory has spaces.
                        command_line = f'"{cmd_exe}" /d /s /c ""{cmd_script}""'
                        result = subprocess.run(command_line, executable=cmd_exe, shell=False,
                                                env=cmd_env, text=True, capture_output=True, timeout=60)
                        if (result.returncode == 0) != succeeds:
                            raise AssertionError(f"CMD install {version}: {result.returncode}\n{result.stdout}\n{result.stderr}")
                        assert cmd_config.read_bytes() == original_config
                        if succeeds:
                            assert cmd_executable.is_file(), "CMD bootstrap did not install wwss"
                            assert Path(resolved.read_text().splitlines()[0]).resolve() == cmd_executable.resolve(), "CMD found the wrong wwss on PATH"
                            expected_version = "v2.0.0" if version is None else "v" + version.removeprefix("v")
                            assert (cmd_install_dir / "version.txt").read_text().strip() == expected_version

                    install_from_cmd("3.0.0", succeeds=False)
                    assert not cmd_executable.exists(), "Failed bootstrap installed an executable"
                    install_from_cmd("v1.0.0")
                    install_from_cmd()  # The published one-line command updates in the same CMD process.
                    install_from_cmd("2.0.0")
                    updated, _ = winreg.QueryValueEx(registry, "Path")
                    assert sum(part.rstrip("\\").lower() == str(cmd_install_dir).lower() for part in updated.split(";")) == 1
                else:
                    for profile in [home / ".bashrc", home / ".profile"]:
                        assert profile.read_text().count("# >>> wwss PATH >>>") == 1
                    resolved = subprocess.run(
                        ["bash", "--noprofile", "-c", '. "$HOME/.bashrc"; command -v wwss; wwss --help >/dev/null'],
                        env=env, text=True, capture_output=True, timeout=15,
                    )
                    assert resolved.returncode == 0 and str(executable) in resolved.stdout, resolved.stderr
                    bootstrap = (
                        'wwss_setup=$(mktemp) && curl -fsSL "' + base_url
                        + '/latest/download/install.sh" -o "$wwss_setup" && sh "$wwss_setup"'
                        + ' && rm -f "$wwss_setup" && export PATH="$HOME/.local/bin:$PATH" && wwss --help'
                    )
                    pasted = subprocess.run(["bash", "--noprofile", "-c", bootstrap], env=env, text=True, capture_output=True, timeout=60)
                    assert pasted.returncode == 0, pasted.stdout + pasted.stderr
                    # Selection tests simulate each Unix OS/CPU; payloads are the host's
                    # native binary so these test installer routing, not cross-OS execution.
                    for goos, machine, shell, silicon in [
                        ("Linux", "x86_64", "/bin/bash", "0"),
                        ("Linux", "aarch64", "/bin/bash", "0"),
                        ("Darwin", "x86_64", "/bin/zsh", "0"),
                        ("Darwin", "arm64", "/bin/zsh", "1"),
                        ("Darwin", "x86_64", "/bin/zsh", "1"),
                    ]:
                        scenario = root / (goos + machine + silicon)
                        scenario.mkdir()
                        wrappers = scenario / "commands"
                        wrappers.mkdir()
                        for name, body in {
                            "uname": f'if [ "$1" = -s ]; then echo {goos}; else echo {machine}; fi',
                            "sysctl": f"echo {silicon}", "getconf": "echo 64",
                        }.items():
                            path = wrappers / name
                            path.write_text("#!/bin/sh\n" + body + "\n")
                            path.chmod(0o755)
                        simulated = dict(env, HOME=str(scenario), SHELL=shell, PATH=str(wrappers) + os.pathsep + env["PATH"])
                        install("1.0.0", custom_env=simulated)
                        expected_arch = "arm64" if machine in ["arm64", "aarch64"] or silicon == "1" else "amd64"
                        assert f"{goos.lower()}/{expected_arch}" in (scenario / ".local/share/wwss/README.md").read_text()
                        if shell.endswith("zsh"):
                            assert (scenario / ".zshrc").read_text().count("# >>> wwss PATH >>>") == 1
                        (wrappers / "uname").write_text("#!/bin/sh\necho unsupported\n")
                        install("1.0.0", succeeds=False, custom_env=simulated)
                print("Installer checks passed: install/update, PATH, configuration preservation, checksum/download failures, and native command execution.")
            finally:
                server.shutdown()
                server.server_close()
    finally:
        if registry is not None:
            import winreg
            if saved_user_path is None:
                try:
                    winreg.DeleteValue(registry, "Path")
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(registry, "Path", 0, saved_user_path[1], saved_user_path[0])
            registry.Close()


if __name__ == "__main__":
    main()
