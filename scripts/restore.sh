#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
full=false
snapshot=false
options=()
for arg in "$@"; do
    case "$arg" in
        --full) full=true ;;
        --snapshot|--snapshot=*) snapshot=true; options+=("$arg") ;;
        -h|--help)
            echo 'Usage: restore.sh [--full] [--profile generic|desktop] [--dry-run] [--yes] [--snapshot ID_OR_LATEST]'
            echo '--full installs desktop and app packages (including AUR), then restores configs.'
            echo 'Without --full, only managed configuration files are restored.'
            exit 0 ;;
        *) options+=("$arg") ;;
    esac
done
if $full; then
    if $snapshot; then
        echo '--full cannot be combined with --snapshot: snapshots recover config files only.' >&2
        exit 1
    fi
    exec "$script_dir/setup.sh" --apps --aur "${options[@]}"
fi
if ! command -v python3 >/dev/null; then
    echo 'Python 3 is required: sudo pacman -S --needed python' >&2
    exit 1
fi
exec python3 "$script_dir/dotfiles.py" restore "${options[@]}"
