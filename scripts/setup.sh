#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(dirname -- "$script_dir")
profile=''
aur=false
skip_packages=false
dry_run=false
yes=false
while (($#)); do
    case "$1" in
        --profile)
            [[ $# -ge 2 && "$2" =~ ^(generic|desktop)$ ]] || { echo 'Expected --profile generic|desktop' >&2; exit 1; }
            profile=$2; shift 2 ;;
        --aur) aur=true; shift ;;
        --skip-packages) skip_packages=true; shift ;;
        --dry-run) dry_run=true; shift ;;
        --yes) yes=true; shift ;;
        -h|--help)
            echo 'Usage: setup.sh [--profile generic|desktop] [--aur] [--skip-packages] [--dry-run] [--yes]'
            echo 'Installs dependencies, snapshots/restores configs, and registers Fish commands.'
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done
config_dir=${XDG_CONFIG_HOME:-"$HOME/.config"}
if [[ -z "$profile" && -f "$config_dir/dotfiles/profile" ]]; then
    profile=$(< "$config_dir/dotfiles/profile")
fi
if [[ -z "$profile" ]]; then
    if $yes || $dry_run; then
        profile=generic
    else
        read -r -p 'Profile: generic (automatic displays) or desktop (DP-1 1440p/165 Hz) [generic]: ' profile
        profile=${profile:-generic}
    fi
fi
[[ "$profile" =~ ^(generic|desktop)$ ]] || { echo 'Invalid profile' >&2; exit 1; }
if ! $skip_packages; then
    options=()
    $aur && options+=(--aur)
    $dry_run && options+=(--dry-run)
    "$script_dir/install-packages.sh" "${options[@]}"
fi
options=(--profile "$profile")
$dry_run && options+=(--dry-run)
$yes && options+=(--yes)
"$script_dir/restore.sh" "${options[@]}"
if ! $dry_run; then
    # restore installs the wrapper functions and writes local registration state.
    echo "Setup complete. Checkout: $repo"
    echo 'Open Fish to use dots-setup, dots-backup, and dots-restore.'
    echo 'Choose niri at login. No display manager, login shell, or system service was changed.'
    echo 'See docs/setup.md for optional themes, portals, and personal Fish settings.'
fi
