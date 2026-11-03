function dots-backup --description 'Dotfiles backup'
    set -l registration "$__fish_config_dir/../dotfiles/repository"
    if not test -f "$registration"
        echo "Run scripts/register-fish.sh from your dotfiles checkout first." >&2
        return 1
    end
    set -l repo (string collect < "$registration")
    if not test -x "$repo/scripts/backup.sh"
        echo "Dotfiles checkout moved; rerun scripts/register-fish.sh." >&2
        return 1
    end
    "$repo/scripts/backup.sh" $argv
end
