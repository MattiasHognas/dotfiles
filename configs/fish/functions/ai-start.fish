function ai-start --description 'Start Strata and ComfyUI'
    set -l strata_dir "$HOME/Applications/Strata"
    set -l comfy_dir "$HOME/Applications/ComfyUI"
    set -l output_dir "$HOME/Pictures/ComfyUI"
    set -l strata_url http://127.0.0.1:8080
    set -l comfy_url  http://127.0.0.1:8188
    
    if not curl -s --max-time 2 "$strata_url/health" >/dev/null
        kitty --detach --hold --title Strata --directory "$strata_dir" \
                        "$strata_dir/setup.sh"
    end
    
    if not curl -s --max-time 2 "$comfy_url/system_stats" >/dev/null
        mkdir -p "$output_dir"; or return 1
        kitty --detach --hold --title ComfyUI --directory "$comfy_dir" \
                        "$comfy_dir/.venv/bin/python" main.py \
                        --listen 127.0.0.1 --port 8188 --cache-none --disable-metadata \
                        --output-directory "$output_dir"
    end
    
    printf '\nStrata   %s\nComfyUI  %s\n\n' "$strata_url" "$comfy_url"
end
