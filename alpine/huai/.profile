# Default applications and locale
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim

# Path settings
export PATH="$HOME/.local/bin:$PATH"

# File creation mask
umask 022

# Ensure runtime directory exists for PipeWire sockets (available in non-interactive sessions)
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR="/tmp/user-$(id -u)"
    [ ! -d "$XDG_RUNTIME_DIR" ] && mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"
fi


# Return early if running non-interactively (aliases, prompt, and tty setup below)
case "$-" in
    *i*) ;;
    *) return ;;
esac

# Prompt formatting (ash compatible ANSI color escapes)
export PS1='[1;33m\h[0m [1;32m\u[0m[1;35m:\w\$[0m '

# GPG configuration
if [ -t 0 ]; then
    export GPG_TTY=$(tty)
    gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1
fi

# SSH agent setup
export SSH_AUTH_SOCK="/tmp/ssh-agent-$USER.socket"
if ! pgrep -u "$USER" -x ssh-agent >/dev/null; then
    rm -f "$SSH_AUTH_SOCK"
    eval "$(ssh-agent -s -a "$SSH_AUTH_SOCK")" >/dev/null
fi

# Source external aliases file if it exists
[ -f "$HOME/.aliases" ] && . "$HOME/.aliases"