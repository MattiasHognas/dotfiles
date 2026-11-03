#!/usr/bin/env bash
set -euo pipefail
dry_run=false
for arg in "$@"; do
    case "$arg" in
        --dry-run) dry_run=true ;;
        -h|--help) echo 'Usage: install-haskell.sh [--dry-run]'; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done
if [[ -n ${GHCUP_USE_XDG_DIRS:-} ]]; then
    echo 'This setup uses the standard GHCup layout; unset GHCUP_USE_XDG_DIRS or manage that installation separately.' >&2
    exit 1
fi
ghcup_base=${GHCUP_INSTALL_BASE_PREFIX:-"$HOME"}
[[ "$ghcup_base" == /* ]] || { echo 'GHCUP_INSTALL_BASE_PREFIX must be absolute.' >&2; exit 1; }
ghcup_bin="$ghcup_base/.ghcup/bin"
if ! $dry_run && ((EUID == 0)); then
    echo 'Run Haskell setup as your normal user, without sudo.' >&2
    exit 1
fi
if [[ ! -x "$ghcup_bin/ghcup" ]]; then
    if $dry_run; then
        echo "Would bootstrap GHCup from https://get-ghcup.haskell.org into $ghcup_bin"
    else
        command -v curl >/dev/null || { echo 'Install repository prerequisites first (setup.sh --apps).' >&2; exit 1; }
        bootstrap=$(mktemp)
        trap 'rm -f -- "$bootstrap"' EXIT
        curl --proto '=https' --tlsv1.2 -fsSL https://get-ghcup.haskell.org -o "$bootstrap"
        GHCUP_INSTALL_BASE_PREFIX="$ghcup_base" \
            BOOTSTRAP_HASKELL_NONINTERACTIVE=1 BOOTSTRAP_HASKELL_MINIMAL=1 \
            BOOTSTRAP_HASKELL_ADJUST_BASHRC='' BOOTSTRAP_HASKELL_ADJUST_CABAL_CONFIG='' \
            BOOTSTRAP_HASKELL_NO_UPGRADE=1 sh "$bootstrap"
        [[ -x "$ghcup_bin/ghcup" ]] || { echo 'GHCup bootstrap did not create its executable.' >&2; exit 1; }
    fi
fi
for tool in ghc cabal stack hls; do
    executable=$tool
    [[ "$tool" == hls ]] && executable=haskell-language-server-wrapper
    if [[ -x "$ghcup_bin/$executable" ]]; then
        echo "Keeping selected $tool ($ghcup_bin/$executable)"
    elif $dry_run; then
        printf 'Would run: %q install %q recommended --set\n' "$ghcup_bin/ghcup" "$tool"
    else
        GHCUP_INSTALL_BASE_PREFIX="$ghcup_base" "$ghcup_bin/ghcup" install "$tool" recommended --set
    fi
    if ! $dry_run; then
        "$ghcup_bin/$executable" --version
    fi
done
if ! $dry_run; then
    echo 'Haskell tools ready. The managed Fish config adds GHCup and Cabal executables to PATH.'
fi
