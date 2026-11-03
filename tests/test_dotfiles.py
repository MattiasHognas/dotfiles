import importlib.util
import json
import os
from pathlib import Path
import pty
import shutil
import subprocess
import tempfile
import tomllib
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class DotfilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dots tests ")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "checkout with spaces"
        shutil.copytree(SOURCE, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.home = self.base / "home with spaces"
        self.home.mkdir()
        self.config = self.home / ".config"
        self.state = self.home / ".local/state"
        self.env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.config),
                        XDG_STATE_HOME=str(self.state), XDG_CACHE_HOME=str(self.home / ".cache"))
        self.env.pop("NOCTALIA_STATE_HOME", None)
        self.env.pop("NOCTALIA_CONFIG_HOME", None)
        self.env.pop("NIRI_CONFIG", None)

    def command(self, name, *args, ok=True, tty=False):
        argv = [str(self.repo / "scripts" / (name + ".sh")), *args]
        if tty:
            master, slave = pty.openpty()
            try:
                process = subprocess.Popen(argv, env=self.env, stdin=slave, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, text=True)
                os.write(master, b"yes\n")
                output, _ = process.communicate(timeout=30)
                result = subprocess.CompletedProcess(argv, process.returncode, output, "")
            finally:
                os.close(master)
                os.close(slave)
        else:
            result = subprocess.run(argv, env=self.env, capture_output=True, text=True, timeout=30)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def install(self, profile="generic"):
        return self.command("setup", "--skip-packages", "--yes", "--profile", profile)

    def snapshots(self):
        return sorted((self.state / "dotfiles/backups").glob("*/snapshot.json"))

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=self.env,
                              check=True, capture_output=True, text=True).stdout.strip()

    def test_fresh_install_and_idempotence(self):
        self.install()
        self.assertEqual((self.config / "dotfiles/profile").read_text().strip(), "generic")
        self.assertNotIn("DP-1", (self.config / "niri/outputs.kdl").read_text())
        self.assertEqual((self.config / "dotfiles/wallpaper").read_bytes(), (self.repo / "assets/wallpaper").read_bytes())
        settings = tomllib.loads((self.state / "noctalia/settings.toml").read_text())
        self.assertEqual(settings["theme"]["mode"], "dark")
        self.assertNotIn("hyprland", settings["theme"]["templates"]["builtin_ids"])
        self.assertEqual(settings["wallpaper"]["default"]["path"], str(self.config / "dotfiles/wallpaper"))
        self.assertNotIn("monitors", settings["wallpaper"])
        snapshots = self.snapshots()
        self.install()
        self.assertEqual(snapshots, self.snapshots())

    def test_backup_restore_and_permissions(self):
        self.install()
        path = self.config / "kitty/kitty.conf"
        path.write_text(path.read_text() + "\n# test preference\n")
        path.chmod(0o600)
        self.command("backup")
        saved = path.read_bytes()
        path.write_text("# temporary edit\n")
        self.command("restore", "--yes")
        self.assertEqual(path.read_bytes(), saved)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_snapshot_restores_absence_and_keeps_unmanaged_files(self):
        self.install()
        initial = self.snapshots()[0].parent.name
        unmanaged = self.config / "kitty/unmanaged.conf"
        unmanaged.write_text("keep me")
        self.command("restore", "--snapshot", initial, "--yes")
        self.assertFalse((self.config / "kitty/kitty.conf").exists())
        self.assertFalse((self.config / "gtk-4.0/assets").is_symlink())
        self.assertFalse((self.state / "noctalia/settings.toml").exists())
        self.assertEqual(unmanaged.read_text(), "keep me")

    def test_latest_is_resolved_before_recovery_snapshot(self):
        self.install()
        path = self.config / "kitty/kitty.conf"
        path.write_text("# chosen state\n")
        self.command("backup")
        path.write_text("# changed after backup\n")
        self.command("restore", "--snapshot", "latest", "--yes")
        self.assertEqual(path.read_text(), "# chosen state\n")

    def test_missing_live_file_does_not_delete_repository_copy(self):
        self.install()
        source = self.repo / "configs/kitty/kitty.conf"
        original = source.read_bytes()
        (self.config / "kitty/kitty.conf").unlink()
        result = self.command("backup")
        self.assertIn("MISSING kitty/kitty.conf", result.stdout)
        self.assertEqual(source.read_bytes(), original)

    def test_profile_isolation_and_private_preferences(self):
        generic = (self.repo / "profiles/generic/noctalia-settings.toml").read_bytes()
        self.install("desktop")
        path = self.state / "noctalia/settings.toml"
        text = path.read_text().replace('"address" = ""', '"address" = "Private town"')
        text = text.replace('"avatar_path" = ""', '"avatar_path" = "/private/avatar.png"')
        path.write_text(text)
        self.command("backup")
        captured = (self.repo / "profiles/desktop/noctalia-settings.toml").read_text()
        self.assertNotIn("Private town", captured)
        self.assertNotIn("/private/avatar.png", captured)
        self.assertNotIn(str(self.home), captured)
        self.assertEqual((self.repo / "profiles/generic/noctalia-settings.toml").read_bytes(), generic)
        self.command("restore", "--yes")
        restored = tomllib.loads(path.read_text())
        self.assertEqual(restored["location"]["address"], "Private town")
        self.assertEqual(restored["shell"]["avatar_path"], "/private/avatar.png")

    def test_active_wallpaper_is_captured(self):
        self.install()
        image = self.home / "new background.jpg"
        # A different valid JPEG fixture without image conversion.
        image.write_bytes((self.repo / "assets/wallpaper").read_bytes() + b"test trailing data")
        settings = self.state / "noctalia/settings.toml"
        settings.write_text(settings.read_text().replace(str(self.config / "dotfiles/wallpaper"), str(image)))
        self.command("backup")
        self.assertEqual((self.repo / "assets/wallpaper").read_bytes(), image.read_bytes())
        self.assertTrue((self.snapshots()[-1].parent / "selected-wallpaper").exists())
        self.assertNotIn(str(image), (self.repo / "profiles/generic/noctalia-settings.toml").read_text())

    def test_restore_dry_run_does_not_write(self):
        self.command("restore", "--profile", "generic", "--dry-run")
        self.assertEqual(list(self.home.iterdir()), [])

    def test_backup_dry_run_does_not_write(self):
        self.install()
        old = (self.repo / "configs/kitty/kitty.conf").read_bytes()
        (self.config / "kitty/kitty.conf").write_text("# changed\n")
        snapshots = self.snapshots()
        self.command("backup", "--dry-run")
        self.assertEqual((self.repo / "configs/kitty/kitty.conf").read_bytes(), old)
        self.assertEqual(snapshots, self.snapshots())

    def test_unexpected_symlink_rejected_before_any_restore(self):
        self.config.mkdir()
        target = self.home / "outside"
        target.mkdir()
        (self.config / "kitty").symlink_to(target, target_is_directory=True)
        result = self.command("restore", "--profile", "generic", "--yes", ok=False)
        self.assertIn("symlink", result.stderr)
        self.assertEqual(list(target.iterdir()), [])
        self.assertFalse((self.config / "niri/config.kdl").exists())

    def test_leaf_symlink_rejected(self):
        self.install()
        target = self.home / "outside-file"
        target.write_text("untouched")
        path = self.config / "kitty/kitty.conf"
        path.unlink()
        path.symlink_to(target)
        self.command("restore", "--yes", ok=False)
        self.command("backup", ok=False)
        self.assertEqual(target.read_text(), "untouched")

    def test_manifest_tampering_in_snapshot_rejected(self):
        self.install()
        meta_path = self.snapshots()[0]
        meta = json.loads(meta_path.read_text())
        meta["files"]["../outside"] = {"kind": "absent"}
        meta_path.write_text(json.dumps(meta))
        self.command("restore", "--snapshot", "latest", "--yes", ok=False)
        self.assertTrue((self.config / "kitty/kitty.conf").exists())

    def test_register_commands_and_forward_arguments_with_spaces(self):
        if not shutil.which("fish"):
            self.skipTest("fish unavailable")
        self.command("register-fish", "--profile", "desktop")
        result = subprocess.run(["fish", "-c", "dots-restore --dry-run"], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CHANGE niri/config.kdl", result.stdout)
        self.assertFalse((self.config / "niri/config.kdl").exists())

    def test_restore_requires_confirmation(self):
        self.command("restore", "--profile", "generic", ok=False)
        self.assertFalse((self.config / "niri/config.kdl").exists())

    def test_push_failure_keeps_commit_and_snapshot_then_retries(self):
        self.install()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Dotfiles test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("add", ".")
        self.git("commit", "-m", "Initial")
        remote = self.base / "remote.git"
        self.git("init", "--bare", str(remote))
        self.git("remote", "add", "origin", str(remote))
        hook = remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        path = self.config / "kitty/kitty.conf"
        path.write_text(path.read_text() + "\n# captured change\n")
        before = self.git("rev-parse", "HEAD")
        self.command("backup", "--push", tty=True, ok=False)
        after = self.git("rev-parse", "HEAD")
        self.assertNotEqual(before, after)
        self.assertGreaterEqual(len(self.snapshots()), 2)
        hook.unlink()
        self.command("backup", "--push", tty=True)
        self.assertEqual(self.git("rev-parse", "refs/heads/main", cwd=remote), self.git("rev-parse", "HEAD"))

    def test_push_rejects_existing_staged_changes(self):
        self.install()
        self.git("init", "-b", "main")
        self.git("add", "README.md")
        result = self.command("backup", "--push", ok=False)
        self.assertIn("staged", result.stderr)

    def test_sensitive_toml_values_block_publication(self):
        path = self.repo / "profiles/generic/noctalia-settings.toml"
        path.write_text(path.read_text() + '\n[private]\napi_key = "not-for-github"\n')
        result = subprocess.run(["python3", str(self.repo / "scripts/dotfiles.py"), "scan"],
                                env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("credential", result.stderr)

    def test_package_lists_and_dry_run(self):
        self.command("install-packages", "--dry-run")
        with (self.repo / "packages/official.txt").open("a") as stream:
            stream.write("--malicious-option\n")
        self.command("install-packages", "--dry-run", ok=False)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_fuzzel_config_uses_current_icon_setting(self):
        config = (self.repo / "configs/fuzzel/fuzzel.ini").read_text()
        self.assertIn("icons-enabled=yes", config)
        self.assertNotIn("\nicons=yes", config)

    def test_app_package_selection_and_dry_run(self):
        tools = self.base / "fake package tools"
        tools.mkdir()
        helper = tools / "yay"
        helper.write_text("#!/bin/sh\nexit 99\n")
        helper.chmod(0o755)
        self.env["PATH"] = str(tools) + os.pathsep + self.env["PATH"]
        base = self.command("install-packages", "--dry-run").stdout
        self.assertNotIn(" steam", base)
        result = self.command("install-packages", "--apps", "--aur", "--dry-run").stdout
        for package in ("fish", "niri", "blender", "neovim", "steam", "zed", "zen-browser-bin", "visual-studio-code-bin"):
            self.assertIn(" " + package, result)
        self.assertEqual(list(self.home.iterdir()), [])
        with (self.repo / "packages/apps-aur.txt").open("a") as stream:
            stream.write("--invalid-option\n")
        self.command("install-packages", "--apps", "--dry-run", ok=False)

    def test_full_restore_installs_packages_before_configs(self):
        installer = self.repo / "scripts/install-packages.sh"
        installer.write_text('#!/bin/sh\n'
                             'test ! -f "$XDG_CONFIG_HOME/niri/config.kdl" || exit 90\n'
                             'printf "%s\\n" "$@" > "$HOME/installer-arguments"\n')
        self.command("restore", "--full", "--profile", "desktop", "--yes")
        self.assertEqual((self.home / "installer-arguments").read_text().splitlines(), ["--aur", "--apps"])
        self.assertTrue((self.config / "niri/config.kdl").exists())
        self.assertEqual((self.config / "dotfiles/profile").read_text().strip(), "desktop")

    def test_full_restore_refuses_snapshot_and_stops_on_install_failure(self):
        self.command("restore", "--full", "--snapshot", "latest", ok=False)
        installer = self.repo / "scripts/install-packages.sh"
        installer.write_text('#!/bin/sh\nexit 42\n')
        self.command("restore", "--full", "--profile", "generic", "--yes", ok=False)
        self.assertFalse((self.config / "niri/config.kdl").exists())

    def test_toml_serialization_preserves_nested_values(self):
        spec = importlib.util.spec_from_file_location("dotfiles", SOURCE / "scripts/dotfiles.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = {"quoted.key": {"widgets": [{"id": "clock", "enabled": True, "options": {"size": 1.5}}],
                               "string": 'Swedish åäö "quote"\nnewline', "empty": {}}}
        self.assertEqual(tomllib.loads(module.toml_bytes(data).decode()), data)


if __name__ == "__main__":
    unittest.main()
