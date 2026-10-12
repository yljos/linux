# Return if not interactive
case "$-" in
    *i*) ;;
    *) return ;;
esac

# Set locale
export LANG=en_US.UTF-8

# Set default editors
export VISUAL=vim
export EDITOR=vim

# Set terminal type
export TERM=xterm-256color

# Load aliases if present
if [ -f "$HOME/.aliases" ]; then
    . "$HOME/.aliases"
fi

# ANSI color codes
C_YEL="$(printf '\033[1;33m')"
C_GRN="$(printf '\033[1;32m')"
C_MAG="$(printf '\033[1;35m')"
C_RST="$(printf '\033[0m')"

# Set POSIX-compliant prompt
PS1="${C_YEL}Nas${C_RST} ${C_GRN}\$USER${C_RST}${C_MAG}:\$(pwd)\\\$${C_RST} "
export PS1