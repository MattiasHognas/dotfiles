# Mattias's CachyOS + niri desktop

Plain configuration files and small commands for setting up, backing up, and restoring my desktop. No dotfile manager or symlinks into this checkout: applications use ordinary files in the home directory.

Includes niri, Noctalia 5, the selected background image, Catppuccin colors, Kitty, Fuzzel, Fish, GTK, Qt, and Kvantum settings. Configs follow current CachyOS packages, rather than pinning an entire operating system.

## Install

```bash
sudo pacman -Syu --needed git python
mkdir -p ~/Documents/source
git clone https://github.com/MattiasHognas/dotfiles.git ~/Documents/source/dotfiles
cd ~/Documents/source/dotfiles
./scripts/setup.sh --apps --aur
```

Choose **generic** for automatic monitor configuration, or **desktop** for my DP-1 display (2560×1440, 165 Hz, VRR). With `--apps --aur`, setup includes the desktop, everyday applications, and theme packages. Setup installs repository packages, previews configuration changes, saves a recovery snapshot, restores files, and registers Fish commands. Package updates and the restore each retain their normal confirmation prompts.

`--apps` includes the everyday apps, development toolchains, containers, AI clients, creative tools, and gaming utilities selected from this workstation. `--aur` adds TruffleHog, VS Code, Aseprite, Spotify/Spicetify, and Catppuccin theme packages. Setup installs `yay` and the build tools through pacman before using AUR; review prompts remain enabled. With `--apps`, it also installs missing Haskell tools through GHCup and compatible .NET 10/11 SDKs with the .NET 11 WASM workloads. Omit both flags for the core desktop only. See the [package selection and fresh-install steps](docs/packages.md) for the complete coverage and remaining account/service setup.

## Everyday use

```fish
dots-backup                       # Snapshot live settings, then update local repo copies
dots-backup --push                # Review, confirm, commit selected files, and push
dots-restore --dry-run            # Preview repo -> machine changes
dots-restore                      # Snapshot current settings, then restore configs
dots-restore --full               # Install desktop + apps + AUR packages, then restore configs
dots-restore --snapshot latest    # Restore the latest local recovery snapshot
dots-setup --apps --aur           # Full setup; remembers this machine's profile
```

Edit configs normally or use Noctalia's settings UI, then run `dots-backup`. It captures the active Noctalia settings and selected default wallpaper (JPEG, PNG, or WebP up to 25 MiB). The image is stored as `assets/wallpaper`; its format is detected from its contents. All monitors use that selected background on restore. Separate per-monitor image collections are not included.

Backup does **not** commit, upload, or pull unless requested. `--push` requires an interactive review and clean Git staging area; it stages only files managed by this checkout. It pushes the current branch, including any earlier local commits. Before showing the diff, TruffleHog scans the captured files and local Git history. Missing TruffleHog, findings, or scanner errors block publication while preserving the local backup. Scans disable credential verification and automatic updates. Ordinary backups and config-only restores do not require the scanner. Full restore installs `trufflehog-bin` from AUR; no scanner settings or credentials need backing up. GitHub authentication must already be configured, for example through `gh auth setup-git` or your Git credential manager.

To receive changes from GitHub:

```fish
git -C ~/Documents/source/dotfiles pull --ff-only
dots-restore
```

Run `dots-backup` and commit your local changes before pulling if you have preferences to keep. If a push fails, the local commit and snapshot remain; fix authentication/connectivity and retry `dots-backup --push` or `git push`.

Full restore installs current versions from Arch/CachyOS/AUR, including Fish and niri. It does not pin old versions or remove other installed packages. The curated app lists are `packages/apps-official.txt` and `packages/apps-aur.txt`; add package names there as needed. Steam requires the multilib repository (normally enabled on CachyOS). Blender is installed from the repository instead of recreating a manually downloaded copy. Browser profiles/sign-ins, Steam games, projects, and editor extensions/settings are not part of app installation. The list explicitly includes X11 application support, audio, networking/Bluetooth tools, file browsing, archives, fonts, and codecs; hardware drivers and kernels remain the CachyOS installer’s responsibility.

## What's stored

| Location | Contents |
| --- | --- |
| `configs/` | Shared, ordinary application config files |
| `profiles/generic/` | Automatic monitors and portable Noctalia settings |
| `profiles/desktop/` | My monitor layout and Noctalia settings |
| `assets/wallpaper` | The selected background image |
| `manifest.json` | Exact list of files the scripts manage |
| `packages/` | Core desktop dependencies and curated application lists, separated by repository/AUR |
| `scripts/` | Setup, backup/restore, and Haskell/.NET installers |
| `toolchains/` | Project-compatible .NET SDK channels and workloads |

Noctalia profiles are complete small TOML files: GUI changes update only the active profile. Shared niri settings are in `configs/niri/config.kdl`; monitor settings are in `profiles/*/outputs.kdl`.

Local snapshots live in `~/.local/state/dotfiles/backups/`, outside Git, with original permissions and presence/absence recorded. Config and state locations respect `XDG_CONFIG_HOME` and `XDG_STATE_HOME`; Noctalia's settings also respect `NOCTALIA_STATE_HOME`. Fish resolves this checkout through `~/.config/dotfiles/repository`. If you move the repo, run `./scripts/register-fish.sh` from its new location.

Only manifest files are copied. Clipboard, notifications, browser profiles, credentials, Fish history/universal state, and the rest of Pictures are excluded. Weather location and avatar paths remain local. Personal Fish initialization belongs in `~/.config/fish/local.fish`. Snapshots can contain private settings, so keep them local.

See [setup details](docs/setup.md), [recovery](docs/recovery.md), [keybindings](docs/keybindings.md), and [third-party assets](docs/third-party.md).

See [verification and remaining fresh-install checks](docs/verification.md) for what has actually been tested.

## Checks

```bash
./scripts/check.sh
```

Requires Python 3.11+, Fish, and ShellCheck. Tests use temporary homes and a temporary Git remote. Installed niri and Noctalia binaries also validate the configs. CI checks shell syntax and recovery behavior; full desktop smoke tests require a Wayland session.

To scan the repository history manually (findings may contain secrets, so keep the output private):

```sh
trufflehog git "file://$PWD" --no-verification --no-update --no-ignore-tag --results=verified,unverified,unknown,filtered_unverified --fail --fail-on-scan-errors
```

Run this from the checkout. A clean scan reduces risk but does not guarantee that every secret format is detected. Direct `git push` bypasses the backup script's checks.
