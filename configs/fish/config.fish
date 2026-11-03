if test -f /usr/share/cachyos-fish-config/cachyos-config.fish
    source /usr/share/cachyos-fish-config/cachyos-config.fish
end

set -gx QT_QPA_PLATFORMTHEME qt6ct
set -gx QT_STYLE_OVERRIDE kvantum
set -gx GTK_THEME catppuccin-mocha-mauve-standard+default
fish_add_path --path "$HOME/.local/bin"

# GHCup toolchains and executables installed with cabal install.
set -q GHCUP_INSTALL_BASE_PREFIX; or set -gx GHCUP_INSTALL_BASE_PREFIX "$HOME"
fish_add_path --path "$HOME/.cabal/bin"
fish_add_path --path "$GHCUP_INSTALL_BASE_PREFIX/.ghcup/bin"

# Prefer user SDKs when present; the system SDK remains available otherwise.
set -l dots_dotnet_root "$HOME/.dotnet"
set -q DOTNET_ROOT; and set dots_dotnet_root "$DOTNET_ROOT"
if test -x "$dots_dotnet_root/dotnet"
    set -gx DOTNET_ROOT "$dots_dotnet_root"
    fish_add_path --path "$DOTNET_ROOT/tools"
    fish_add_path --path "$DOTNET_ROOT"
end

function update
    sudo cachyos-rate-mirrors; or return 1
    yay -Syu
end

# Optional personal/development settings; never tracked by dots-backup.
if test -f "$__fish_config_dir/local.fish"
    source "$__fish_config_dir/local.fish"
end
