# =============================================================================
# 1. ENVIRONMENT & EDITOR SETTINGS
# =============================================================================

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
export TERM=xterm-256color 
export GPG_TTY=$(tty)

if [ -f ~/.gnupg/gpg-agent.conf ]; then
    gpgconf --launch gpg-agent  
fi

# =============================================================================
# 2. OH MY ZSH CONFIGURATION
# =============================================================================

export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
CASE_SENSITIVE="true"

plugins=(
  zsh-autosuggestions
  zsh-syntax-highlighting
)

source $ZSH/oh-my-zsh.sh
PROMPT='%F{yellow}Win%f %F{green}%n%f%F{magenta}:%~%F{magenta}$%f '
setopt HIST_IGNORE_ALL_DUPS
# =============================================================================
# 3. CUSTOM ALIASES
# =============================================================================

# Load custom aliases if file exists
if [ -f ~/.aliases ]; then
    source ~/.aliases
fi
export PATH="/c/Windows/System32/OpenSSH:$PATH"

export PATH="$PATH:/c/Program Files/VSCodium-win32-x64-1.108.20787/bin"
export PATH="$PATH:/c/Program Files (x86)/cloudflared"
