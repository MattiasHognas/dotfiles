#!/usr/bin/env python3
"""Install missing project-compatible .NET SDKs and workloads per user."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request

REPO = Path(__file__).resolve().parents[1]
INSTALLER = "https://dot.net/v1/dotnet-install.sh"


def download_installer(destination):
    with urllib.request.urlopen(INSTALLER, timeout=60) as response:
        destination.write_bytes(response.read())


def install(dry_run=False):
    root = Path(os.environ.get("DOTNET_ROOT", Path.home() / ".dotnet"))
    if not root.is_absolute():
        raise ValueError("DOTNET_ROOT must be an absolute path")
    if not dry_run and os.geteuid() == 0:
        raise ValueError("Run .NET setup as your normal user, without sudo")
    executable = root / "dotnet"
    specs = json.loads((REPO / "toolchains/dotnet.json").read_text())
    environment = dict(os.environ, DOTNET_ROOT=str(root), DOTNET_ROOT_X64=str(root),
                       DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1",
                       DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE="true")
    with tempfile.TemporaryDirectory(prefix="dots-dotnet-") as temporary:
        work = Path(temporary)
        installer = work / "dotnet-install.sh"
        for index, spec in enumerate(specs):
            # The SDK resolver honors the same minimum and roll-forward rules as the projects.
            (work / "global.json").write_text(json.dumps({"sdk": spec["sdk"]}))
            selected = None
            if executable.is_file():
                result = subprocess.run([str(executable), "--version"], cwd=work, env=environment,
                                        capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    selected = result.stdout.strip()
            if selected:
                print(f"Keeping compatible .NET SDK {selected}", flush=True)
            elif dry_run:
                print(f"Would install .NET channel {spec['channel']} ({spec['quality']}) into {root}", flush=True)
            else:
                if not installer.exists():
                    download_installer(installer)
                command = ["bash", str(installer), "--channel", spec["channel"], "--quality", spec["quality"],
                           "--install-dir", str(root), "--no-path"]
                # Specs are newest first; older SDKs must not replace the newer dotnet host.
                if index:
                    command.append("--skip-non-versioned-files")
                subprocess.run(command, cwd=work, env=environment, check=True)
                subprocess.run([str(executable), "--version"], cwd=work, env=environment, check=True)
            workloads = spec["workloads"]
            if not workloads:
                continue
            installed = set()
            if selected or not dry_run:
                result = subprocess.run([str(executable), "workload", "list"], cwd=work, env=environment,
                                        capture_output=True, text=True, check=True)
                installed = {line.split()[0] for line in result.stdout.splitlines() if line.split()}
            missing = [name for name in workloads if name not in installed]
            if missing and dry_run:
                print(f"Would install .NET {spec['channel']} workloads: {', '.join(missing)}", flush=True)
            elif missing:
                subprocess.run([str(executable), "workload", "install", *missing],
                               cwd=work, env=environment, check=True)
            else:
                print(f".NET {spec['channel']} workloads already installed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        install(args.dry_run)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"ERROR: {error}\n")
