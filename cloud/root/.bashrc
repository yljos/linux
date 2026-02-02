# If not running interactively, don't do anything
[[ $- != *i* ]] && return
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
PS1='\[\e[1;33m\]Cloud\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '
[ -z "$TMUX" ] && [[ "$TERM" == "xterm" ]] && export TERM=xterm-256color
[[ -f ~/.aliases ]] && . ~/.aliases
