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
| Development | .NET 10 and 11 SDKs/WASM workloads, GHCup/GHC/Cabal/Stack/HLS, Node/npm/pnpm/Corepack, Rustup, Rust Analyzer, Go/gopls, C/C++ build tools, Just, Lazygit, tmux |
| Diagnostics | btop, fastfetch, GDB, LLDB, Valgrind, strace, Hyperfine, Ghidra |
| Containers | Podman, Compose/Desktop, rootless networking/storage, QEMU user emulation |
| AI tools | Codex CLI, Claude Code, Claude Desktop |
| Creative and media | Blender, Krita, Aseprite, DaVinci Resolve, Ardour, audio plugins/routing, Typst, FFmpeg, VLC/codecs, Spotify/Spicetify |
| Games | Steam, ProtonUp-Qt, MangoHud, GameMode, Wine, Sunshine |
| Appearance | Catppuccin GTK/Kvantum/cursors and Papirus folder colors, plus the managed theme configs |

`packages/official.txt` is the core desktop. `packages/apps-official.txt` adds the workstation applications. Their `aur.txt` counterparts contain the packages sourced from AUR. The checked list has 141 repository targets and 9 AUR targets, plus the Haskell and .NET toolchain downloads; these numbers exclude automatically resolved dependencies.

Repository packages are installed first with a full system update. This includes `yay` and `base-devel`, so a clean CachyOS install does not need an AUR helper in advance. An existing `paru` can also be used. AUR package review/build prompts remain interactive. With `--apps`, repository/AUR packages are followed by Haskell and .NET toolchain setup. If any installation fails, config restoration does not proceed. `--skip-packages` skips both packages and toolchain installation.

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

Rustup is a toolchain manager: on a new machine, run `rustup default stable` to install Rust/Cargo. Node and Go are installed directly. Haskell and the project-compatible .NET SDKs are handled automatically as described below. Other project-specific SDKs/workloads, Python environments, npm packages, and Cargo tools belong to their projects.

## Deliberately left to the machine or project

The lists exclude the old alternate desktop pieces (KWin, Polybar, Rofi, Dunst, extra display managers), kernel/boot/filesystem packages, NVIDIA/AMD drivers, CUDA/OpenCL choices, hardware fan-controller modules, and niche cross-compilers. CachyOS should select hardware support for the actual machine, including the matching 32-bit GPU libraries for Steam. DaVinci Resolve may require additional GPU compute support for that hardware.

Personal configurations for the additional applications, browser profiles, SSH keys, project files, and game libraries are not in the manifest. Keep those in the appropriate private backup or account sync. Local dotfile snapshots are separate from this public repository.

Package list edits are ordinary Git changes. `dots-backup --push` stages captured configs and the selected wallpaper, not package-list edits; commit those with Git when changing the install selection.

## Haskell

`setup.sh --apps` and `dots-restore --full` run `scripts/install-haskell.sh` after the system dependencies are installed. It bootstraps [GHCup](https://www.haskell.org/ghcup/install/) from the official installer, then installs and selects recommended GHC, Cabal, Stack, and Haskell Language Server versions when those tools are missing. Existing selected tools are retained and checked with their version commands. The installer does not append to shell startup files; the managed Fish config adds `~/.ghcup/bin` and `~/.cabal/bin` to PATH.

Recommended versions are GHCup's curated defaults, rather than a frozen copy of the old workstation. Use `ghcup tui` for additional compiler versions required by projects. The standard GHCup layout is used; `GHCUP_INSTALL_BASE_PREFIX` is supported, while GHCup's optional XDG layout is not managed. Editor integration still needs the relevant extension, such as `haskell.haskell` in VS Code.

## .NET SDKs and WASM workloads

The repository package `dotnet-sdk` provides a system installation. The dotfiles additionally restore the user SDK setup under `~/.dotnet`, because the system package alone may not meet project requirements. Fish prefers that installation and exposes `~/.dotnet/tools`.

`scripts/install-dotnet.sh` reads `toolchains/dotnet.json` and uses the SDK resolver's `global.json` rules to keep compatible installed SDKs. Missing SDKs are fetched with Microsoft's [dotnet-install script](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-install-script). The current selection is:

- .NET 10 GA channel, with 10.0.400 as the minimum and `latestFeature` roll-forward, for Ashes.
- .NET 11 preview channel, with 11.0.100-rc.2.26504.105 as the minimum and `latestFeature` roll-forward, for StickAndPuck.
- `wasm-tools` and `wasm-experimental` workloads installed using the selected .NET 11 SDK.

The minimum versions express project compatibility, not exact download pins. New SDKs come from the configured channel. Update the .NET 11 quality to `GA` when moving the projects to the stable release. Installation checks that the downloaded SDK satisfies the resolver before continuing. Workload checks run outside the caller's project so another `global.json` cannot select the wrong SDK. The newest SDK is processed first, and older SDK installation preserves its host files.

Existing compatible SDKs and installed workloads are not automatically upgraded on every restore. Use normal SDK/workload updates when wanted. `DOTNET_ROOT` may select a different absolute user-owned installation directory. Run these helpers without sudo:

```bash
./scripts/install-haskell.sh --dry-run
./scripts/install-dotnet.sh --dry-run
```

Neither installer publishes toolchain directories, NuGet/Cabal caches, or credentials to Git. Large SDK/compiler downloads are normal on a fresh machine.
