# Exit if not an interactive shell.
case $- in
    *i*) ;;
      *) return;;
esac
# Environment Variables
#export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/ssh-agent.socket"
export SSH_AUTH_SOCK="$(gpgconf --list-dirs agent-ssh-socket)"
export MAILCAPS="$HOME/.config/mutt/mailcap"
export GPG_TTY=$(tty)
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
# 历史记录不存重复项
setopt HIST_IGNORE_ALL_DUPS   # 如果新增命令已经存在于历史中，则删除之前的，保留最新的
setopt HIST_SAVE_NO_DUPS      # 保存到文件时不写入重复项
setopt HIST_IGNORE_DUPS       # 连续重复命令不记录
setopt HIST_FIND_NO_DUPS      # 搜索历史时跳过重复项

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
# Get current TTY device name
current_tty=$(tty)

if [[ "$current_tty" == /dev/tty* ]]; then
    x >/dev/null 2>&1
# elif [[ "$current_tty" == /dev/pts* ]]; then
#     notify-send "zshrc reloaded " >/dev/null 2>&1
fi
