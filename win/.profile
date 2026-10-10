# Set locale
export LANG=en_US.UTF-8

# Append application path
export PATH="$PATH:/c/Program Files/VSCodium-win32-x64-1.108.20787/bin"

# Configure GPG environment
export GPG_TTY=$(tty 2>/dev/null)
if [ -f "$HOME/.gnupg/gpg-agent.conf" ]; then
    gpgconf --launch gpg-agent
fi

# ANSI color codes
C_YEL="$(printf '\033[1;33m')"
C_GRN="$(printf '\033[1;32m')"
C_MAG="$(printf '\033[1;35m')"
C_RST="$(printf '\033[0m')"

# Set POSIX-compliant prompt
PS1="${C_YEL}Win${C_RST} ${C_GRN}\$USER${C_RST}${C_MAG}:\$(pwd)\\\$${C_RST} "
export PS1