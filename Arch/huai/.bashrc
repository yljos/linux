# If not running interactively, don't do anything
[[ $- != *i* ]] && return
export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/ssh-agent.socket"
export MAILCAPS="$HOME/.config/mutt/mailcap"
export GPG_TTY=$(tty)
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
umask 022
[[ -r /usr/share/bash-completion/bash_completion ]] && . /usr/share/bash-completion/bash_completion
[[ -f ~/.aliases ]] && . ~/.aliases
# Bash specific prompt and environment
PS1='\[\e[1;33m\]\h\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '

