import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1]


class ToolchainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dots toolchains ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        shutil.copytree(SOURCE, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "calls"
        self.env = dict(os.environ, HOME=str(self.home), GHCUP_INSTALL_BASE_PREFIX=str(self.home),
                        DOTNET_ROOT=str(self.home / ".dotnet"), DOTNET_ROOT_X64=str(self.home / ".dotnet"),
                        PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        DOTS_TEST_LOG=str(self.log))
        self.env.pop("GHCUP_USE_XDG_DIRS", None)

    def executable(self, path, contents):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        path.chmod(0o755)
        return path

    def run_script(self, name, *args, ok=True):
        result = subprocess.run([str(self.repo / "scripts" / name), *args], env=self.env,
                                capture_output=True, text=True, timeout=30)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def fake_ghcup(self):
        return self.executable(self.root / "fake-ghcup", '''#!/bin/bash
printf '%s\\n' "$*" >> "$DOTS_TEST_LOG"
[[ ${DOTS_TEST_FAIL_HASKELL:-0} == 1 ]] && exit 42
tool=$2
[[ "$tool" == hls ]] && tool=haskell-language-server-wrapper
printf '#!/bin/sh\\necho "fixture tool version"\\n' > "$GHCUP_INSTALL_BASE_PREFIX/.ghcup/bin/$tool"
chmod +x "$GHCUP_INSTALL_BASE_PREFIX/.ghcup/bin/$tool"
''')

    def test_haskell_dry_run_is_offline_and_does_not_write(self):
        result = self.run_script("install-haskell.sh", "--dry-run")
        self.assertIn("Would bootstrap GHCup", result.stdout)
        self.assertIn("install hls recommended --set", result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_haskell_bootstrap_installs_four_tools_and_keeps_them_on_rerun(self):
        self.env["DOTS_TEST_GHCUP"] = str(self.fake_ghcup())
        self.executable(self.bin / "curl", '''#!/bin/bash
while (($#)); do
    if [[ "$1" == -o ]]; then target=$2; break; fi
    shift
done
cat > "$target" <<'SCRIPT'
test "$BOOTSTRAP_HASKELL_MINIMAL" = 1 || exit 90
test -z "$BOOTSTRAP_HASKELL_ADJUST_BASHRC" || exit 91
mkdir -p "$GHCUP_INSTALL_BASE_PREFIX/.ghcup/bin"
cp "$DOTS_TEST_GHCUP" "$GHCUP_INSTALL_BASE_PREFIX/.ghcup/bin/ghcup"
SCRIPT
''')
        self.run_script("install-haskell.sh")
        calls = self.log.read_text().splitlines()
        self.assertEqual(calls, [f"install {tool} recommended --set" for tool in ("ghc", "cabal", "stack", "hls")])
        self.run_script("install-haskell.sh")
        self.assertEqual(self.log.read_text().splitlines(), calls)
        self.assertFalse((self.home / ".bashrc").exists())

    def test_haskell_install_failure_stops_remaining_tools(self):
        self.executable(self.home / ".ghcup/bin/ghcup", self.fake_ghcup().read_text())
        self.env["DOTS_TEST_FAIL_HASKELL"] = "1"
        self.run_script("install-haskell.sh", ok=False)
        self.assertEqual(self.log.read_text().splitlines(), ["install ghc recommended --set"])

    def dotnet_module(self):
        spec = importlib.util.spec_from_file_location("install_dotnet", self.repo / "scripts/install_dotnet.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def dotnet_fixture(self):
        return '''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
root=Path(os.environ["DOTNET_ROOT"])
sdk=json.loads(Path("global.json").read_text())["sdk"]["version"]
channel=".".join(sdk.split(".")[:2])
if sys.argv[1:] == ["--version"]:
    if not (root / ("sdk-"+channel)).exists(): sys.exit(1)
    print(sdk)
elif sys.argv[1:] == ["workload","list"]:
    file=root/("workloads-"+channel)
    print(file.read_text() if file.exists() else "")
elif sys.argv[1:3] == ["workload","install"]:
    with open(os.environ["DOTS_TEST_LOG"],"a") as stream: stream.write("workloads "+channel+" "+" ".join(sys.argv[3:])+"\\n")
    (root/("workloads-"+channel)).write_text("\\n".join(sys.argv[3:]))
else: sys.exit(90)
'''

    def test_dotnet_dry_run_is_offline_and_does_not_write(self):
        result = self.run_script("install-dotnet.sh", "--dry-run")
        self.assertIn("11.0 (preview)", result.stdout)
        self.assertIn("10.0 (GA)", result.stdout)
        self.assertIn("wasm-tools, wasm-experimental", result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_dotnet_installs_sdk_channels_then_workloads_and_is_repeatable(self):
        module = self.dotnet_module()
        source = self.executable(self.root / "fake-dotnet", self.dotnet_fixture())
        self.env["DOTS_TEST_DOTNET"] = str(source)
        def download(path):
            path.write_text('''#!/bin/bash
printf 'sdk:%s\\n' "$*" >> "$DOTS_TEST_LOG"
while (($#)); do
    case "$1" in
        --channel) channel=$2; shift 2 ;;
        --install-dir) target=$2; shift 2 ;;
        *) shift ;;
    esac
done
mkdir -p "$target"
cp "$DOTS_TEST_DOTNET" "$target/dotnet"
touch "$target/sdk-$channel"
''')
        with mock.patch.dict(os.environ, self.env, clear=True), mock.patch.object(module, "download_installer", download):
            module.install()
            calls = self.log.read_text().splitlines()
            self.assertEqual(len(calls), 3)
            self.assertIn("--channel 11.0 --quality preview", calls[0])
            self.assertEqual(calls[1], "workloads 11.0 wasm-tools wasm-experimental")
            self.assertIn("--channel 10.0 --quality GA", calls[2])
            self.assertIn("--skip-non-versioned-files", calls[2])
            module.install()
            self.assertEqual(self.log.read_text().splitlines(), calls)

    def test_toolchain_failure_stops_full_restore_before_configs(self):
        self.executable(self.repo / "scripts/install-packages.sh", "#!/bin/sh\nexit 0\n")
        self.executable(self.repo / "scripts/install-haskell.sh", "#!/bin/sh\nexit 42\n")
        self.run_script("restore.sh", "--full", "--profile", "generic", "--yes", ok=False)
        self.assertFalse((self.home / ".config/niri/config.kdl").exists())

    def test_fish_exposes_haskell_and_dotnet_tools(self):
        if not shutil.which("fish"):
            self.skipTest("fish unavailable")
        for relative in (".ghcup/bin/ghc", ".cabal/bin/test-cabal-app", ".dotnet/dotnet", ".dotnet/tools/test-dotnet-tool"):
            self.executable(self.home / relative, "#!/bin/sh\nexit 0\n")
        # Load only this config, without host/global Fish configuration.
        command = f'source "{self.repo}/configs/fish/config.fish"; command -s ghc dotnet test-cabal-app test-dotnet-tool'
        result = subprocess.run(["fish", "--no-config", "-c", command], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for relative in (".ghcup/bin/ghc", ".cabal/bin/test-cabal-app", ".dotnet/dotnet", ".dotnet/tools/test-dotnet-tool"):
            self.assertIn(str(self.home / relative), result.stdout)


if __name__ == "__main__":
    unittest.main()
