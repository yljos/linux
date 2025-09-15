# 1. Exit if not an interactive shell.
case $- in
    *i*) ;;
      *) return;;
esac

# ===================================================================
# 2. Common Configuration (loaded by both TTY and GUI terminals)
# ===================================================================

# Environment Variables
export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/ssh-agent.socket"
export MAILCAPS="$HOME/.config/mutt/mailcap"
export GPG_TTY=$(tty)
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
umask 022

# Aliases
if [ -f ~/.aliases ]; then
    source ~/.aliases
fi

# ===================================================================
# 3. Handle TTY Environment
# ===================================================================

# If in a TTY, stop here after loading the common configuration.
if [[ "$TERM" = "linux" ]]; then
  return
fi

# ===================================================================
# 4. GUI Terminal-Only Configuration (not loaded in TTY)
# ===================================================================

# Powerlevel10k Instant Prompt
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Oh My Zsh & Powerlevel10k Theme Configuration
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="powerlevel10k/powerlevel10k"
plugins=(zsh-autosuggestions zsh-syntax-highlighting)
source $ZSH/oh-my-zsh.sh

# Powerlevel10k Specific Configuration File
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Aliases
if [ -f ~/.aliases ]; then
    source ~/.aliases
fi
