# Set locale
export LANG=en_US.UTF-8

# Append application path
export PATH="$PATH:/c/Program Files/VSCodium-win32-x64-1.108.20787/bin"

# Configure GPG environment
export GPG_TTY=$(tty 2>/dev/null)
if [ -f "$HOME/.gnupg/gpg-agent.conf" ]; then
    gpgconf --launch gpg-agent
fi

# Set custom PS1 prompt
export PS1='\[\e[1;33m\]Win\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '