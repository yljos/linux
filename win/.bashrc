# 1. 设置颜色和提示符
PS1='\[\e[1;33m\]Win\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '

# 2. 启动并配置 GPG 代理作为 SSH Agent
if [ -f ~/.gnupg/gpg-agent.conf ]; then
    # 确保 GPG 代理已启动
    gpgconf --launch gpg-agent  
fi