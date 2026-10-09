# Set environment variables
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
export TERM=xterm-256color

# Ensure runtime directory exists for user sessions
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR="/tmp/user-$(id -u)"
    [ ! -d "$XDG_RUNTIME_DIR" ] && mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"
fi

# Return early if running non-interactively
case "$-" in
    *i*) ;;
    *) return ;;
esac

# Interactive prompt (ash/sh compatible)
export PS1='[1;33mNas[0m [1;32m\u[0m[1;35m:\w\$[0m '

# Source external aliases file if it exists
[ -f "$HOME/.aliases" ] && . "$HOME/.aliases"