# 设置 TTY 终端
export GPG_TTY=$(tty)

# 指定 SSH 代理的 Socket 路径
export SSH_AUTH_SOCK=$(gpgconf --list-dirs agent-ssh-socket)

# 确保 gpg-agent 已经启动
gpgconf --launch gpg-agent

# 更新当前 TTY 信息，确保密码输入框 (pinentry) 在当前窗口弹出
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1

PS1='\[\e[1;33m\]Pixel4XL\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '
