# Restoring a working CachyOS workstation

Start with an installed CachyOS desktop and working internet. Let the CachyOS installer configure the disks, bootloader, kernel, firmware, GPU drivers, and login manager for the machine.

```bash
sudo pacman -Syu --needed git python
mkdir -p ~/Documents/source
git clone https://github.com/MattiasHognas/dotfiles.git ~/Documents/source/dotfiles
cd ~/Documents/source/dotfiles
./scripts/setup.sh --apps --aur
```

Choose `desktop` for the original DP-1 monitor or `generic` for another machine. To preview everything, append `--dry-run`. Once installed, `dots-restore --full` repeats the same package-and-config flow.

The package lists use current repository versions. They deliberately select useful applications and supporting components from the original workstation instead of replaying every installed package. Dependencies are resolved by pacman and the AUR helper.

## Included

| Area | Main components |
| --- | --- |
| Setup | Git, GitHub CLI, Python, base-devel, yay |
| Desktop | niri, Noctalia, Fish, Kitty, Fuzzel, screenshot tools, Xwayland Satellite, desktop portals, keyring |
| Desktop integration | PipeWire/WirePlumber, NetworkManager, Bluetooth/Blueman, brightness/power support, GTK/Qt integration |
| Files and text | Thunar, USB/MTP access, thumbnails, archive tools, fonts including emoji/CJK, ripgrep, fd, jq, rsync |
| Everyday apps | Zen, VS Code, Neovim, Zed, Obsidian, LibreOffice, LocalSend, Meld, Flatpak |
| Development | .NET SDK, Node/npm/pnpm/Corepack, Rustup, Rust Analyzer, Go/gopls, C/C++ build tools, Just, Lazygit, tmux |
| Diagnostics | btop, fastfetch, GDB, LLDB, Valgrind, strace, Hyperfine, Ghidra |
| Containers | Podman, Compose/Desktop, rootless networking/storage, QEMU user emulation |
| AI tools | Codex CLI, Claude Code, Claude Desktop |
| Creative and media | Blender, Krita, Aseprite, DaVinci Resolve, Ardour, audio plugins/routing, Typst, FFmpeg, VLC/codecs, Spotify/Spicetify |
| Games | Steam, ProtonUp-Qt, MangoHud, GameMode, Wine, Sunshine |
| Appearance | Catppuccin GTK/Kvantum/cursors and Papirus folder colors, plus the managed theme configs |

`packages/official.txt` is the core desktop. `packages/apps-official.txt` adds the workstation applications. Their `aur.txt` counterparts contain the packages sourced from AUR. The checked list has 134 repository targets and 8 AUR targets; these numbers exclude automatically resolved dependencies.

Repository packages are installed first with a full system update. This includes `yay` and `base-devel`, so a clean CachyOS install does not need an AUR helper in advance. An existing `paru` can also be used. AUR package review/build prompts remain interactive. If installation fails, config restoration does not proceed.

Arch, CachyOS, and multilib repositories must be enabled. Steam needs multilib; applications such as Zen, Claude Desktop, and DaVinci Resolve are supplied by CachyOS. Package installation does not configure app accounts, download Steam games, restore documents, or install editor extensions.

## After the first installation

Select **niri** at the login screen. To make Fish your login shell, run `chsh -s /usr/bin/fish`, then log out and back in. The scripts install Fish and its commands but do not change your account's login shell.

On a normal CachyOS desktop the essential services may already be enabled. If networking, Bluetooth, or power controls are unavailable, inspect them with:

```bash
systemctl status NetworkManager bluetooth power-profiles-daemon
```

Enable a missing service as appropriate, for example `sudo systemctl enable --now bluetooth`. Audio uses the PipeWire user services; if needed after logging into niri:

```bash
systemctl --user enable --now pipewire.socket pipewire-pulse.socket wireplumber.service
```

The setup does not switch networking services or start an SSH server, game-streaming server, or container daemon. Sunshine pairing and streaming access are configured in the app. Podman runs without a daemon; Podman Desktop may guide you through its initial setup.

Authenticate GitHub with `gh auth login` and `gh auth setup-git`. Sign into Zen/browser sync, Steam, Spotify, and the AI tools separately. Credentials remain outside the public repo.

Rustup is a toolchain manager: on a new machine, run `rustup default stable` to install Rust/Cargo. Node, Go, and the distro .NET SDK are installed directly. Project-specific SDK versions, .NET workloads, Python environments, npm packages, and Cargo tools belong to their projects. Existing Haskell/GHCup installations are not cloned by this repo; restore that toolchain separately if needed.

## Deliberately left to the machine or project

The lists exclude the old alternate desktop pieces (KWin, Polybar, Rofi, Dunst, extra display managers), kernel/boot/filesystem packages, NVIDIA/AMD drivers, CUDA/OpenCL choices, hardware fan-controller modules, and niche cross-compilers. CachyOS should select hardware support for the actual machine, including the matching 32-bit GPU libraries for Steam. DaVinci Resolve may require additional GPU compute support for that hardware.

Personal configurations for the additional applications, browser profiles, SSH keys, project files, and game libraries are not in the manifest. Keep those in the appropriate private backup or account sync. Local dotfile snapshots are separate from this public repository.

Package list edits are ordinary Git changes. `dots-backup --push` stages captured configs and the selected wallpaper, not package-list edits; commit those with Git when changing the install selection.
