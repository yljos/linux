# Ensure interactive child shells source this profile for aliases
export ENV="$HOME/.profile"

# Return early if running non-interactively
case "$-" in
    *i*) ;;
    *) return ;;
esac

# Default applications and locale
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim

# Path settings
export PATH="$HOME/.local/bin:$PATH"

# Prompt formatting (ash compatible ANSI color escapes)
export PS1='[1;33m\h[0m [1;32m\u[0m[1;35m:\w\$[0m '

# File creation mask
umask 022

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

# Basic system aliases
alias ls='ls --color=auto'
alias grep='grep --color=auto'
alias c="clear"
alias ..='cd ..'
alias vi='vim'

alias rsyncdir="rsync -avzh --delete"

# Pipewire volume control
alias volup="wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+"
alias voldown="wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"

# User script shortcuts (executed with /bin/sh)
alias win="/bin/sh /home/huai/.config/win.sh"
alias hiwin="/bin/sh /home/huai/.config/wake.sh"
alias x="startx"
alias np="/bin/sh /home/huai/.config/wallpaper.sh"

# NFS4 mount function
mount-data() {
    if ! mountpoint -q /data; then
        sudo mount -t nfs4 10.0.0.21:/data /data
    fi
}