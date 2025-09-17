#!/usr/bin/dash
MIRRORLIST_PATH="/etc/pacman.d/mirrorlist"
TSINGHUA_URL="https://mirrors.tuna.tsinghua.edu.cn/archlinux/"
# Check if reflector is installed
if ! command -v reflector >/dev/null 2>&1; then
    echo "reflector is not installed, installing..."
    sudo pacman -S --noconfirm reflector
fi
update_mirrors() {
    # The command to be executed is passed as arguments to this function
    if sudo reflector "$@"; then
        cat "$MIRRORLIST_PATH"
    else
        exit 1
    fi
}

# if [ -z "$1" ] checks if the first argument is empty (i.e., no arguments were given)
if [ -z "$1" ]; then
    # DEFAULT BEHAVIOR: No arguments provided, use Tsinghua mirror
    update_mirrors \
        --url "$TSINGHUA_URL" \
        --save "$MIRRORLIST_PATH"
else
    # OPTIONAL BEHAVIOR: Any argument provided, find the fastest mirrors
    update_mirrors \
        -c China \
        -a 12 \
        -p https \
        --score 5 \
        --sort rate \
        -n 3 \
        --ipv4 \
        --save "$MIRRORLIST_PATH" >/dev/null 2>&1
fi
cat "$MIRRORLIST_PATH"