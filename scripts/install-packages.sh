#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(dirname -- "$script_dir")
aur=false
apps=false
dry_run=false
for arg in "$@"; do
    case "$arg" in
        --aur) aur=true ;;
        --apps) apps=true ;;
        --dry-run) dry_run=true ;;
        -h|--help) echo 'Usage: install-packages.sh [--apps] [--aur] [--dry-run]'; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done
read_packages() {
    local line
    while IFS= read -r line || [[ -n "$line" ]]; do
        line=${line%%#*}
        [[ -z "$line" ]] && continue
        [[ "$line" =~ ^[a-z0-9][a-z0-9@._+-]*$ ]] || { echo "Invalid package name: $line" >&2; return 1; }
        printf '%s\n' "$line"
    done < "$1"
}
# Capture first so invalid lists propagate an error, rather than hiding it in process substitution.
official_text=$(read_packages "$repo/packages/official.txt")
aur_text=$(read_packages "$repo/packages/aur.txt")
if $apps; then
    official_text+=$'\n'$(read_packages "$repo/packages/apps-official.txt")
    aur_text+=$'\n'$(read_packages "$repo/packages/apps-aur.txt")
fi
mapfile -t official_packages <<< "$official_text"
mapfile -t aur_packages <<< "$aur_text"
helper=''
if $aur; then
    if command -v yay >/dev/null; then helper=yay
    elif command -v paru >/dev/null; then helper=paru
    else echo 'Install yay or paru manually before using --aur.' >&2; exit 1
    fi
fi
if $dry_run; then
    printf 'Would run: sudo pacman -Syu --needed'; printf ' %q' "${official_packages[@]}"; printf '\n'
    if $aur; then
        printf 'Would run: %s -S --needed' "$helper"; printf ' %q' "${aur_packages[@]}"; printf '\n'
    else
        echo 'AUR packages skipped; use --aur to include the listed themes and selected AUR apps.'
    fi
    exit 0
fi
if ! command -v pacman >/dev/null || ! [[ -f /etc/cachyos-release ]] && ! grep -q '^ID=cachyos$' /etc/os-release; then
    echo 'Package installation targets CachyOS. Use setup --skip-packages elsewhere.' >&2
    exit 1
fi
if ((EUID == 0)); then
    echo 'Run as your normal user; sudo is used only for pacman.' >&2
    exit 1
fi
sudo pacman -Syu --needed "${official_packages[@]}"
if $aur; then
    "$helper" -S --needed "${aur_packages[@]}"
else
    echo 'AUR packages skipped. Use --aur to include the listed themes and selected AUR apps.'
fi
