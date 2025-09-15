# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

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

# If in a TTY, stop here after loading the common configuration.
if [[ "$TERM" = "linux" ]]; then
  alias x="sh /home/huai/.config/dwl/dwl_status.sh | dwl"
  return
fi


# Powerlevel10k Instant Prompt
local p10k_cache_file="${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
[[ -r "$p10k_cache_file" ]] && source "$p10k_cache_file"
# Oh My Zsh & Powerlevel10k Theme Configuration
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="powerlevel10k/powerlevel10k"
plugins=(zsh-autosuggestions zsh-syntax-highlighting)
source $ZSH/oh-my-zsh.sh

# Powerlevel10k Specific Configuration File
[[ -f ~/.p10k.zsh ]] && source ~/.p10k.zsh

# Aliases
[[ -f ~/.aliases ]] && source ~/.aliases

# To customize prompt, run `p10k configure` or edit /workspace/linux/arch/huai/.p10k.zsh.
[[ ! -f /workspace/linux/arch/huai/.p10k.zsh ]] || source /workspace/linux/arch/huai/.p10k.zsh
