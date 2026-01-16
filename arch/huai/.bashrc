# If not running interactively, don't do anything
[[ $- != *i* ]] && return

#export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/ssh-agent.socket"
export SSH_AUTH_SOCK="$(gpgconf --list-dirs agent-ssh-socket)"
export MAILCAPS="$HOME/.config/mutt/mailcap"
export GPG_TTY=$(tty)
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1
export LANG=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim

# --- 历史记录配置 ---
# ignoreboth: 等同于 ignoredups (忽略连续重复) + ignorespace (忽略以空格开头的命令)
# erasedups: 清除整个历史记录中已存在的相同命令，确保记录唯一
export HISTCONTROL=ignoreboth:erasedups
# 建议同时加上追加模式，防止多终端覆盖历史
shopt -s histappend 
# ------------------

umask 022
[[ -r /usr/share/bash-completion/bash_completion ]] && . /usr/share/bash-completion/bash_completion
[[ -f ~/.aliases ]] && . ~/.aliases

# Bash specific prompt and environment
PS1='\[\e[1;33m\]\h\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '

# Get current TTY device name
current_tty=$(tty)

if [[ "$current_tty" == /dev/tty* ]]; then
    x > /dev/null 2>&1 
# elif [[ "$current_tty" == /dev/pts* ]]; then
#     notify-send "bashrc reloaded" >/dev/null 2>&1
fi
