export GPG_TTY=$(tty)
if [ -z "$SSH_AUTH_SOCK" ]; then
    eval "$(ssh-agent -s)" > /dev/null
fi

gpgconf --launch gpg-agent
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1

PS1='\[\e[1;33m\]Pixel4XL\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '
