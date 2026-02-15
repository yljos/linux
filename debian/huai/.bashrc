[[ $- != *i* ]] && return

export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
export GPG_TTY=$(tty)
export SSH_AUTH_SOCK="$(gpgconf --list-dirs agent-ssh-socket)"

gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1

export HISTSIZE=10000
export HISTFILESIZE=20000
export HISTCONTROL=ignoreboth:erasedups
shopt -s histappend

umask 022

[[ -f /usr/share/bash-completion/bash_completion ]] && . /usr/share/bash-completion/bash_completion
[[ -f ~/.aliases ]] && . ~/.aliases

export TERM=xterm-256color

PS1='\[\e[1;33m\]Debian\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '

if [[ -z $DISPLAY ]] && [[ $(tty) == /dev/tty1 ]]; then
    [[ -f ~/.xinitrc ]] && command -v startx >/dev/null 2>&1 && exec startx
fi