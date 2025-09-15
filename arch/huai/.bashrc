# If not running interactively, don't do anything
[[ $- != *i* ]] && return
export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/ssh-agent.socket"
export MAILCAPS="$HOME/.config/mutt/mailcap"
export GPG_TTY=$(tty)
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
# If in a TTY, stop here after loading the common configuration.
if [[ "$TERM" = "linux" ]]; then
  alias x="sh /home/huai/.config/dwl/dwl_status.sh | dwl"
  return
fi
umask 022
[[ -r /usr/share/bash-completion/bash_completion ]] && . /usr/share/bash-completion/bash_completion

# Bash specific prompt and environment
PS1='\[\e[1;33m\]\h\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '

if [ -f ~/.aliases ]; then
    source ~/.aliases
fi
