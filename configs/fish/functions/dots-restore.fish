function dots-restore --description 'Dotfiles restore'
    set -l registration "$__fish_config_dir/../dotfiles/repository"
    if not test -f "$registration"
        echo "Run scripts/register-fish.sh from your dotfiles checkout first." >&2
        return 1
    end
    set -l repo (string collect < "$registration")
    if not test -x "$repo/scripts/restore.sh"
        echo "Dotfiles checkout moved; rerun scripts/register-fish.sh." >&2
        return 1
    end
    "$repo/scripts/restore.sh" $argv
end
