PS1='\[\e[1;33m\]Win\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '

export GPG_TTY=$(tty)
# export SSH_AUTH_SOCK=$(gpgconf --list-dirs agent-ssh-socket)

if [ -f ~/.gnupg/gpg-agent.conf ]; then
    gpgconf --launch gpg-agent
fi

# Define fixed agent socket path
export SSH_AUTH_SOCK="$HOME/.ssh/agent.sock"

# Check if socket is valid, start agent if not
if ! ssh-add -l > /dev/null 2>&1; then
    if [ ! -S "$SSH_AUTH_SOCK" ] || ! pgrep -u "$USER" ssh-agent > /dev/null; then
        rm -f "$SSH_AUTH_SOCK"
        eval "$(ssh-agent -a "$SSH_AUTH_SOCK")" > /dev/null
    fi
fi

alias key='ssh-add -l >/dev/null 2>&1 || ssh-add "$HOME/.ssh/id_ed25519"'


export HISTCONTROL=ignoreboth:erasedups
shopt -s histappend 
export LANG=en_US.UTF-8

export PATH=$PATH:"/c/Program Files/VSCodium-win32-x64-1.108.20787/bin"