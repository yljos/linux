# Exit if not an interactive shell.
case $- in
    *i*) ;;
      *) return;;
esac
# Environment Variables
export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/ssh-agent.socket"
export MAILCAPS="$HOME/.config/mutt/mailcap"
export GPG_TTY=$(tty)
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
umask 022
CASE_SENSITIVE="true"
# Powerlevel10k Instant Prompt
local p10k_cache_file="${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
[[ -r "$p10k_cache_file" ]] && . "$p10k_cache_file"
# Oh My Zsh & Powerlevel10k Theme Configuration
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="powerlevel10k/powerlevel10k"
plugins=(zsh-autosuggestions zsh-syntax-highlighting)
source $ZSH/oh-my-zsh.sh

# Powerlevel10k Specific Configuration File
[[ -f ~/.p10k.zsh ]] && . ~/.p10k.zsh

# Aliases
[[ -f ~/.aliases ]] && . ~/.aliases