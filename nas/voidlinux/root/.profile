
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

# Set prompt
export PS1='\[\e[1;33m\]Nas\[\e[0m\] \[\e[1;32m\]\u\[\e[0m\]\[\e[1;35m\]:\w\$\[\e[0m\] '