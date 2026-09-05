# If not running interactively, don't do anything
[[ $- != *i* ]] && return

export GPG_TTY=$(tty)
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1
# ssh-agent
export SSH_AUTH_SOCK="/tmp/ssh-agent-$USER.socket"
if ! pgrep -u "$USER" ssh-agent >/dev/null; then
    rm -f "$SSH_AUTH_SOCK"
    eval "$(ssh-agent -s -a "$SSH_AUTH_SOCK")" >/dev/null
fi

export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim


export HISTCONTROL=ignoreboth:erasedups
shopt -s histappend 
# ------------------

umask 022
[[ -r /usr/share/bash-completion/bash_completion ]] && . /usr/share/bash-completion/bash_completion
[[ -f ~/.aliases ]] && . ~/.aliases

# Bash specific prompt and environment
PS1='\[\e[1;33m\]\h\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '


# uv
export PATH="/home/huai/.local/bin:$PATH"

# pipewire
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR="/tmp/user-$(id -u)"
    [ ! -d "$XDG_RUNTIME_DIR" ] && mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"
fi
