case $- in # check shell options
    *i*) ;; # interactive shell
      *) return;; # don't do anything
esac
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
export ZSH="$HOME/.oh-my-zsh"
. "/home/huai/.acme.sh/acme.sh.env"
# Powerlevel10k Instant Prompt
local p10k_cache_file="${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
[[ -r "$p10k_cache_file" ]] && . "$p10k_cache_file"

ZSH_THEME="powerlevel10k/powerlevel10k"

CASE_SENSITIVE="true"

plugins=(zsh-autosuggestions zsh-syntax-highlighting)

source $ZSH/oh-my-zsh.sh


[[ -f ~/.p10k.zsh ]] && . ~/.p10k.zsh
[[ -f ~/.aliases ]] && . ~/.aliases

