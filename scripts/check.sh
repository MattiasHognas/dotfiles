#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(dirname -- "$script_dir")
cd -- "$repo"
for script in scripts/*.sh; do bash -n "$script"; done
shellcheck scripts/*.sh
python3 -m unittest discover -s tests -v
python3 scripts/dotfiles.py scan
for profile in generic desktop; do
    python3 scripts/dotfiles.py validate --profile "$profile"
done
echo 'All checks passed.'
