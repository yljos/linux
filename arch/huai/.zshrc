case $- in # check shell options
    *i*) ;; # interactive shell
      *) return;; # don't do anything
esac
export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/ssh-agent.socket"
export MAILCAPS="$HOME/.config/mutt/mailcap"
export GPG_TTY=$(tty)
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
#export TERM=xterm-256color
umask 022
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

export ZSH="$HOME/.oh-my-zsh"


# Uncomment the following line to use case-sensitive completion.
CASE_SENSITIVE="true"

# HYPHEN_INSENSITIVE="true"

plugins=(git zsh-autosuggestions zsh-syntax-highlighting)


# User configuration

# 加载通用别名
if [ -f ~/.aliases ]; then
    source ~/.aliases
fi

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
if [[ "$TERM" = "linux" ]]; then
  ZSH_THEME="robbyrussell"  
else
  ZSH_THEME="powerlevel10k/powerlevel10k"
  [[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
fi

source $ZSH/oh-my-zsh.sh
