PS1='\[\e[1;33m\]Win\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '

export GPG_TTY=$(tty)
export SSH_AUTH_SOCK=$(gpgconf --list-dirs agent-ssh-socket)

if [ -f ~/.gnupg/gpg-agent.conf ]; then
    gpgconf --launch gpg-agent  
fi
export HISTCONTROL=ignoreboth:erasedups
shopt -s histappend 
export LANG=en_US.UTF-8

export PATH=$PATH:"/c/Users/huai/program/VSCodium-win32-x64-1.107.18627/bin"