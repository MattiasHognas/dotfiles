if test -f /usr/share/cachyos-fish-config/cachyos-config.fish
    source /usr/share/cachyos-fish-config/cachyos-config.fish
end

set -gx QT_QPA_PLATFORMTHEME qt6ct
set -gx QT_STYLE_OVERRIDE kvantum
set -gx GTK_THEME catppuccin-mocha-mauve-standard+default
fish_add_path --path "$HOME/.local/bin"

function update
    sudo cachyos-rate-mirrors; or return 1
    yay -Syu
end

# Optional personal/development settings; never tracked by dots-backup.
if test -f "$__fish_config_dir/local.fish"
    source "$__fish_config_dir/local.fish"
end
