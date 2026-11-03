#!/usr/bin/env python3
"""Small, explicit file-copy engine for the Bash entrypoints (stdlib only)."""

import argparse
import contextlib
import datetime
import difflib
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib

REPO = Path(__file__).resolve().parent.parent
WALLPAPER = "dotfiles/wallpaper"
NOCTALIA = "noctalia/settings.toml"


def toml_bytes(value):
    """Serialize TOML data without a third-party runtime dependency."""
    def scalar(item):
        if isinstance(item, str):
            return json.dumps(item, ensure_ascii=False)
        if isinstance(item, bool):
            return str(item).lower()
        if isinstance(item, (int, float)):
            return str(item)
        if isinstance(item, (datetime.datetime, datetime.date, datetime.time)):
            return item.isoformat()
        if isinstance(item, list):
            return "[" + ", ".join(scalar(i) for i in item) + "]"
        if isinstance(item, dict):
            return "{ " + ", ".join(json.dumps(k) + " = " + scalar(v) for k, v in item.items()) + " }"
        raise ValueError(f"Unsupported TOML value: {type(item)}")
    lines = []
    def table(obj, keys=()):
        if keys:
            lines.append("\n[" + ".".join(json.dumps(k) for k in keys) + "]")
        for key, item in obj.items():
            if not isinstance(item, dict):
                lines.append(json.dumps(key) + " = " + scalar(item))
        for key, item in obj.items():
            if isinstance(item, dict):
                table(item, (*keys, key))
    table(value)
    data = ("\n".join(lines) + "\n").encode()
    tomllib.loads(data.decode())
    return data


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def safe_path(root, relative, allowed_link=None):
    """Never traverse a symlink, including symlinked parent directories."""
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(p in ("..", ".") for p in rel.parts):
        raise ValueError(f"Unsafe managed path: {relative}")
    path = root / rel
    for parent in reversed(path.parents):
        if parent.is_symlink():
            raise ValueError(f"Refusing symlinked parent: {parent}")
        if parent.exists() and not parent.is_dir():
            raise ValueError(f"Parent is not a directory: {parent}")
    if path.is_symlink():
        if allowed_link is None or os.readlink(path) != allowed_link:
            raise ValueError(f"Refusing unexpected symlink: {path}")
    elif path.exists() and not path.is_file():
        raise ValueError(f"Expected a file, found another type: {path}")
    return path


def atomic_write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".dots-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def read_record(path):
    if path.is_symlink():
        return {"kind": "link", "target": os.readlink(path)}
    if not path.exists():
        return {"kind": "absent"}
    return {"kind": "file", "data": path.read_bytes(),
            "mode": stat.S_IMODE(path.stat().st_mode)}


def write_record(path, record):
    if record["kind"] == "absent":
        path.unlink(missing_ok=True)
    elif record["kind"] == "file":
        atomic_write(path, record["data"], record["mode"])
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Replace the directory entry, never follow the old symlink.
        fd, temporary = tempfile.mkstemp(prefix=".dots-", dir=path.parent)
        os.close(fd)
        os.unlink(temporary)
        try:
            os.symlink(record["target"], temporary)
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)


def portable(value, home, restoring=False):
    if isinstance(value, dict):
        return {key: portable(item, home, restoring) for key, item in value.items()}
    if isinstance(value, list):
        return [portable(item, home, restoring) for item in value]
    if isinstance(value, str):
        old, new = ("~/", str(home) + "/") if restoring else (str(home) + "/", "~/")
        if value.startswith(old):
            return new + value[len(old):]
    return value


class Dotfiles:
    def __init__(self, profile=None):
        self.home = Path.home()
        self.config = Path(os.environ.get("XDG_CONFIG_HOME", self.home / ".config"))
        self.state = Path(os.environ.get("XDG_STATE_HOME", self.home / ".local/state")) / "dotfiles"
        self.noctalia_state = Path(os.environ.get("NOCTALIA_STATE_HOME", self.state.parent))
        if not self.config.is_absolute() or not self.state.is_absolute() or not self.noctalia_state.is_absolute():
            raise ValueError("XDG_CONFIG_HOME and XDG_STATE_HOME must be absolute paths")
        self.registration = safe_path(self.config, "dotfiles/repository")
        self.profile_file = safe_path(self.config, "dotfiles/profile")
        self.profile = profile or (self.profile_file.read_text().strip()
                                   if self.profile_file.exists() else None)
        if self.profile not in (None, "generic", "desktop"):
            raise ValueError("Unknown saved profile; choose --profile generic or desktop")
        self.entries = json.loads((REPO / "manifest.json").read_text())
        paths = [entry["path"] for entry in self.entries]
        if len(paths) != len(set(paths)):
            raise ValueError("Duplicate manifest destinations")

    def require_profile(self):
        if self.profile is None:
            raise ValueError("Run setup first or supply --profile generic|desktop")

    def destination(self, entry):
        root = self.noctalia_state if entry.get("root") == "state" else self.config
        return safe_path(root, entry["path"], entry.get("link"))

    def source(self, entry):
        if "profile" in entry:
            return safe_path(REPO, f"profiles/{self.profile}/{entry['profile']}")
        if "source" in entry:
            return safe_path(REPO, entry["source"])
        return safe_path(REPO, "configs/" + entry["path"])

    def noctalia_data(self, data, restoring=False):
        obj = portable(tomllib.loads(data.decode()), self.home, restoring)
        if restoring:
            previous_path = safe_path(self.noctalia_state, NOCTALIA)
            previous = tomllib.loads(previous_path.read_text()) if previous_path.exists() else {}
            # Keep private preferences on this machine, never in the public repo.
            for section, key in (("location", "address"), ("shell", "avatar_path")):
                obj.setdefault(section, {})[key] = previous.get(section, {}).get(key, "")
            wallpaper = str(self.config / WALLPAPER)
        else:
            for section, key in (("location", "address"), ("shell", "avatar_path")):
                obj.setdefault(section, {}).pop(key, None)
            wallpaper = "~/.config/" + WALLPAPER
        for key in ("default", "last"):
            obj.setdefault("wallpaper", {}).setdefault(key, {})["path"] = wallpaper
        for setting in obj["wallpaper"].get("monitors", {}).values():
            setting["path"] = wallpaper
        # A portable setup contains the selected background, not a library of personal paths.
        if restoring and "favorite" in previous.get("wallpaper", {}):
            obj["wallpaper"]["favorite"] = previous["wallpaper"]["favorite"]
        else:
            obj["wallpaper"].pop("favorite", None)
        return toml_bytes(obj)

    @contextlib.contextmanager
    def lock(self):
        lock_path = safe_path(self.state, "operation.lock")
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        with lock_path.open("a") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError("Another dotfiles operation is running") from exc
            yield

    def capture(self):
        return {e["path"]: read_record(self.destination(e)) for e in self.entries}

    def snapshot(self, records, reason):
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        # Check parents before creating any directories.
        safe_path(self.state, f"backups/{stamp}/snapshot.json")
        folder = self.state / "backups" / stamp
        folder.mkdir(parents=True, mode=0o700)
        metadata = {"version": 1, "profile": self.profile, "reason": reason, "files": {}}
        for name, record in records.items():
            metadata["files"][name] = {k: v for k, v in record.items() if k != "data"}
            if record["kind"] == "file":
                atomic_write(folder / "files" / name, record["data"], 0o600)
        # Written last: an interrupted snapshot is never a recovery candidate.
        atomic_write(folder / "snapshot.json", json_bytes(metadata), 0o600)
        print(f"Snapshot: {folder}")
        return folder

    def load_snapshot(self, name):
        if name == "latest":
            candidates = sorted((self.state / "backups").glob("*/snapshot.json"))
            if not candidates:
                raise ValueError("No completed snapshots exist")
            name = candidates[-1].parent.name
        if not re.fullmatch(r"\d{8}T\d{6}\.\d{6}Z", name):
            raise ValueError("Use a snapshot ID printed by backup, or 'latest'")
        folder = self.state / "backups" / name
        meta = json.loads(safe_path(folder, "snapshot.json").read_text())
        if meta.get("version") != 1 or meta.get("profile") not in ("generic", "desktop"):
            raise ValueError("Unsupported snapshot")
        allowed = {e["path"]: e for e in self.entries}
        if set(meta["files"]) != set(allowed):
            raise ValueError("Snapshot manifest differs; use its matching repository revision")
        records = {}
        for path, item in meta["files"].items():
            record = dict(item)
            if record["kind"] == "file":
                mode = record["mode"]
                if type(mode) is not int or not 0 <= mode <= 0o777:
                    raise ValueError("Unsafe snapshot permissions")
                record["data"] = safe_path(folder, "files/" + path).read_bytes()
            elif record["kind"] == "link":
                if record["target"] != allowed[path].get("link"):
                    raise ValueError("Snapshot contains an unexpected symlink")
            elif record["kind"] != "absent":
                raise ValueError("Unknown snapshot entry type")
            records[path] = record
        return records, meta["profile"]

    def desired(self):
        records = {}
        for entry in self.entries:
            if "link" in entry:
                records[entry["path"]] = {"kind": "link", "target": entry["link"]}
            else:
                record = read_record(self.source(entry))
                if record["kind"] != "file":
                    raise ValueError(f"Missing source file: {self.source(entry)}")
                if entry["path"] == NOCTALIA:
                    record["data"] = self.noctalia_data(record["data"], restoring=True)
                records[entry["path"]] = record
        return records

    def preview(self, current, desired):
        changes = []
        for name, after in desired.items():
            before = current[name]
            if before == after:
                continue
            changes.append(name)
            print(f"CHANGE {name}: {before['kind']} -> {after['kind']}")
            if before["kind"] == after["kind"] == "file":
                if name == WALLPAPER:
                    print(f"Background image: {len(before['data'])} -> {len(after['data'])} bytes")
                    continue
                a = before["data"].decode(errors="replace").splitlines(keepends=True)
                b = after["data"].decode(errors="replace").splitlines(keepends=True)
                sys.stdout.writelines(difflib.unified_diff(a, b, fromfile="live/" + name, tofile="restore/" + name))
                if before["mode"] != after["mode"]:
                    print(f"Mode: {before['mode']:03o} -> {after['mode']:03o}")
        if not changes:
            print("All managed files already match.")
        return changes

    def validate(self, records):
        """Validate staged files before touching the running desktop."""
        with tempfile.TemporaryDirectory(prefix="dots-validate-") as temporary:
            root = Path(temporary)
            for name, record in records.items():
                if record["kind"] == "file":
                    atomic_write(root / name, record["data"], record["mode"])
                    if name.endswith(".json"):
                        json.loads(record["data"])
                    if name.endswith(".toml"):
                        tomllib.loads(record["data"].decode())
            config = root / "niri/config.kdl"
            if shutil.which("niri") and config.exists():
                run("niri", "validate", "-c", str(config))
            if shutil.which("fish"):
                for path in root.rglob("*.fish"):
                    run("fish", "--no-config", "-n", str(path))
            if shutil.which("noctalia") and (root / NOCTALIA).exists():
                run("noctalia", "config", "validate", str(root / NOCTALIA))

    def register(self):
        atomic_write(self.registration, (str(REPO) + "\n").encode(), 0o600)
        atomic_write(self.profile_file, (self.profile + "\n").encode(), 0o600)

    def restore(self, args):
        self.require_profile()
        desired, restored_profile = (self.load_snapshot(args.snapshot) if args.snapshot
                                     else (self.desired(), self.profile))
        current = self.capture()  # Preflight every destination before writing anything.
        changes = self.preview(current, desired)
        # Recovery must allow restoring an exact older/incomplete configuration.
        if not args.snapshot:
            self.validate(desired)
        if args.dry_run:
            return
        if changes and not args.yes:
            confirm("Restore these files? Existing files will be snapshotted.")
        if changes:
            self.snapshot(current, "before-restore")
            for entry in self.entries:
                if entry["path"] in changes:
                    write_record(self.destination(entry), desired[entry["path"]])
        self.profile = restored_profile
        self.register()
        print(f"Restore complete ({self.profile}). Open a new Fish shell for commands.")

    def backup(self, args):
        self.require_profile()
        if args.push:
            self.check_git()
        current = self.capture()
        writes = {}
        wallpaper_record = None
        if current[NOCTALIA]["kind"] == "file":
            settings = tomllib.loads(current[NOCTALIA]["data"].decode())
            selected = settings.get("wallpaper", {}).get("default", {}).get("path")
            if selected:
                image = Path(os.path.expandvars(os.path.expanduser(selected)))
                if not image.is_absolute():
                    raise ValueError("Wallpaper must have an absolute path")
                image = safe_path(Path("/"), str(image).lstrip("/"))
                if not image.is_file():
                    raise ValueError(f"Selected wallpaper is missing: {image}")
                if image.stat().st_size > 25 * 1024 * 1024:
                    raise ValueError("Wallpaper exceeds the 25 MiB repository limit")
                wallpaper_record = read_record(image)
                data = wallpaper_record["data"]
                if not (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n")
                        or (data.startswith(b"RIFF") and data[8:12] == b"WEBP")):
                    raise ValueError("Wallpaper must be a JPEG, PNG, or WebP image")
        for entry in self.entries:
            record = current[entry["path"]]
            if entry["path"] == WALLPAPER and wallpaper_record:
                record = wallpaper_record
            if record["kind"] == "absent":
                print(f"MISSING {entry['path']} (repo copy retained)")
                continue
            if "link" in entry:
                if record["kind"] != "link":
                    raise ValueError(f"Expected configured theme symlink: {entry['path']}")
                continue
            record = dict(record)
            if entry["path"] == NOCTALIA:
                record["data"] = self.noctalia_data(record["data"])
            writes[self.source(entry)] = record
        for path, record in writes.items():
            if read_record(path) != record:
                print(f"CAPTURE {path.relative_to(REPO)}")
        if args.dry_run:
            return
        snapshot = self.snapshot(current, "backup")
        if wallpaper_record:
            atomic_write(snapshot / "selected-wallpaper", wallpaper_record["data"], 0o600)
        for path, record in writes.items():
            write_record(path, record)
        print("Repository configs refreshed. No commit or push unless --push was requested.")
        if args.push:
            self.publish(list(writes))

    def check_git(self):
        root = run("git", "rev-parse", "--show-toplevel", cwd=REPO, capture_output=True, text=True).stdout.strip()
        if Path(root) != REPO:
            raise ValueError("Initialize this checkout as its own Git repository first")
        staged = run("git", "diff", "--cached", "--name-only", cwd=REPO, capture_output=True, text=True).stdout
        if staged:
            raise ValueError("Commit or unstage existing staged changes before --push")
        run("git", "remote", "get-url", "origin", cwd=REPO, capture_output=True)

    def publish(self, paths):
        scan_public_files(paths)
        relative = [str(p.relative_to(REPO)) for p in paths]
        if not relative:
            raise ValueError("No captured files to publish")
        run("git", "--no-pager", "diff", "--", *relative, cwd=REPO)
        untracked = run("git", "ls-files", "--others", "--exclude-standard", "--", *relative,
                        cwd=REPO, capture_output=True, text=True).stdout
        if untracked:
            print("New files:\n" + untracked)
            for path in paths:
                tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", str(path.relative_to(REPO))],
                                         cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                if tracked.returncode:
                    diff = subprocess.run(["git", "--no-pager", "diff", "--no-index", "--", "/dev/null", str(path)],
                                          cwd=REPO, check=False)
                    if diff.returncode not in (0, 1):
                        raise ValueError(f"Could not preview new file: {path}")
        confirm("Commit these managed configs and push this branch to origin?")
        run("git", "add", "--", *relative, cwd=REPO)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO, check=False)
        if diff.returncode == 1:
            run("git", "commit", "-m", "Back up desktop configuration", cwd=REPO)
        elif diff.returncode != 0:
            raise ValueError("Could not inspect staged changes")
        # Also retries a previous failed push when there are no new changes.
        run("git", "push", "-u", "origin", "HEAD", cwd=REPO)


def scan_public_files(paths):
    """A conservative guard, not a replacement for reviewing the Git diff."""
    problems = []
    for path in paths:
        if not path.is_file():
            continue
        if path.name == "wallpaper":
            continue
        text = path.read_text()
        if re.search(r"-----BEGIN .*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]+", text):
            problems.append(str(path))
        if path.suffix in (".json", ".toml"):
            def inspect(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        normalized = key.lower().replace("_", "").replace("-", "")
                        if isinstance(value, str) and value and normalized.endswith(("apikey", "password", "token", "secret", "accesskey")):
                            problems.append(str(path))
                        inspect(value)
                elif isinstance(obj, list):
                    for value in obj:
                        inspect(value)
            inspect(json.loads(text) if path.suffix == ".json" else tomllib.loads(text))
    if problems:
        raise ValueError("Possible credential in these files; remove it before publishing: " + ", ".join(sorted(set(problems))))


def confirm(message):
    if not sys.stdin.isatty():
        raise ValueError("Confirmation requires a terminal (restore supports --yes)")
    if input(message + " [y/N] ").strip().lower() not in ("y", "yes"):
        raise ValueError("Cancelled; nothing published or restored")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("backup", "restore", "register-fish", "validate", "scan"))
    parser.add_argument("--profile", choices=("generic", "desktop"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--snapshot", metavar="ID_OR_LATEST")
    parser.add_argument("--yes", action="store_true", help="Skip restore confirmation; never skips publishing review")
    args = parser.parse_args()
    if args.push and args.command != "backup":
        parser.error("--push applies only to backup")
    if args.snapshot and args.command != "restore":
        parser.error("--snapshot applies only to restore")
    if args.yes and args.command != "restore":
        parser.error("--yes applies only to restore")
    if args.command == "scan":
        scan_public_files(list((REPO / "configs").rglob("*")) + list((REPO / "profiles").rglob("*")))
        print("Public-config credential check passed; still review the diff.")
        return
    dots = Dotfiles(args.profile)
    dots.require_profile()
    if args.command == "validate":
        dots.validate(dots.desired())
        return
    with contextlib.nullcontext() if args.dry_run else dots.lock():
        if args.command == "backup":
            dots.backup(args)
        elif args.command == "restore":
            dots.restore(args)
        elif args.command == "register-fish":
            current = dots.capture()
            names = [e for e in dots.entries if e["path"].startswith("fish/functions/dots-")]
            desired = {e["path"]: read_record(dots.source(e)) for e in names}
            changes = dots.preview(current, desired)
            if not args.dry_run:
                if changes:
                    dots.snapshot(current, "before-register-fish")
                    for entry in names:
                        if entry["path"] in changes:
                            write_record(dots.destination(entry), desired[entry["path"]])
                dots.register()
                print("Fish commands registered. Open a new shell or call dots-backup now.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
