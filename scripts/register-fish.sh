#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if ! command -v python3 >/dev/null; then
    echo 'Python 3 is required: sudo pacman -S --needed python' >&2
    exit 1
fi
exec python3 "$script_dir/dotfiles.py" register-fish "$@"
