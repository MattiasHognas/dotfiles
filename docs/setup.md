# Setup and customization

Use a fresh CachyOS installation and a normal user account. The setup script installs packages through `sudo pacman -Syu --needed`, keeping the system fully updated. It does not format disks, change the bootloader, install GPU drivers, select a display manager, change your login shell, or enable system services.

```bash
./scripts/setup.sh --profile generic --dry-run
./scripts/setup.sh --profile desktop --apps --aur
```

`dots-restore --full` performs the same package installation and config restoration as `dots-setup --apps --aur`. Plain restore and snapshot recovery only affect config files. `--full` cannot be combined with `--snapshot`. Package installation must succeed before configs are restored.

`--dry-run` reports package commands and configuration differences without changing the home directory. `--skip-packages` skips packages and Haskell/.NET toolchain installation when dependencies are already installed. `--yes` skips only the restore confirmation; it does not disable package review or publishing confirmation.

On first setup, back up any personal Fish development initialization to `~/.config/fish/local.fish` before replacing `config.fish`. This local file is sourced at the end of the shared config and is never published by backup. Missing managed files are not removed from the repository during backup.

Select niri at login. CachyOS's existing audio, networking, D-Bus, and session services are assumed. Verify screen sharing and file pickers through the installed XDG desktop portals. Use the distro's normal driver and display-manager configuration for your hardware. The desktop uses the Swedish keyboard layout; edit `configs/niri/config.kdl` if needed.

## Desktop appearance

- niri layout, bindings, startup commands, and Steam window rules: `configs/niri/config.kdl`.
- niri focus/border colors: `configs/niri/noctalia.kdl` (Noctalia-generated; included for first launch).
- Bar, dock, shell colors, theme selection, idle behavior, background, and other GUI settings: `profiles/<profile>/noctalia-settings.toml`.
- Selected background: `assets/wallpaper`, deployed to `~/.config/dotfiles/wallpaper`.
- Terminal, launcher, GTK/Qt theme settings: their corresponding files under `configs/`.

This setup targets **Noctalia 5**, whose GUI settings live in `~/.local/state/noctalia/settings.toml`. Older `~/.config/noctalia/settings.json` and wallpaper-cache JSON files are not used or backed up. See [Noctalia configuration](https://docs.noctalia.dev/noctalia/configuration/).

Noctalia watches its settings for changes. Its theme engine may regenerate niri/Kitty/GTK/Qt colors after restore; those generated files are explicitly managed so a fresh session has colors immediately. `dots-backup` captures their current contents. Community palettes/templates may need network access on a fresh machine.

Backup keeps the selected default background, not favorite wallpaper libraries. Restore retains existing local weather location, avatar, and wallpaper favorites. On a fresh machine these personal preferences start empty. Notifications, clipboard content, and Noctalia's private runtime `state.toml` are never copied.

The optional Catppuccin theme packages provide GTK assets and the Kvantum base theme. The manifest contains two explicit GTK links into `/usr/share/themes/`; all other managed files are copied. An unexpected symlink anywhere in a managed destination or its parents causes a safe failure rather than writing through it.

## Profiles and registration

```bash
./scripts/setup.sh --profile desktop --skip-packages
./scripts/restore.sh --profile generic
./scripts/register-fish.sh --profile desktop
```

Changing profiles takes a snapshot of the current files before applying the selected profile. Backup writes Noctalia settings and monitor settings only into the saved profile. Registering Fish alone does not apply the desktop configs; do that with setup/restore before the first backup to avoid capturing a pre-migration config layout.

Fish functions are ordinary autoloaded files and forward every argument. Registration stores the checkout path separately, so the functions themselves contain no username or hardcoded checkout location.

## Adding a config

Add one explicit file to `manifest.json` and its repository copy under `configs/`. Paths are relative to the config directory unless an entry explicitly selects a state location. Do not add whole application-state directories. Run the checks and inspect `dots-restore --dry-run` before deploying. Review every public diff; the credential check is an extra guard, not a guarantee.

## Application packages

The desktop list includes niri, Fish, Noctalia, Kitty, the launcher, X11 support, audio, networking/Bluetooth integration, file browsing, archives, and fonts. `--apps --aur` adds the curated development, creative, productivity, and gaming workstation packages. Repository installation supplies `yay` and `base-devel` before the AUR phase, so there is no separate AUR-helper bootstrap step.

See [package coverage and fresh-install activation steps](packages.md) for the selection, services, toolchains, and app sign-ins. All packages use the current versions in the configured repositories. Keep Arch/CachyOS repositories and multilib enabled.

Edit `packages/apps-official.txt` or `packages/apps-aur.txt` to change the app selection. Commit package-list edits with normal Git commands; `dots-backup --push` only stages captured configs and the selected wallpaper. The lists are curated and are not automatically replaced with every package on the machine.
