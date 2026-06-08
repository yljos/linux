# =============================================================================
# 1. ENVIRONMENT & EDITOR SETTINGS
# =============================================================================

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
export TERM=xterm-256color 

# =============================================================================
# 2. OH MY ZSH CONFIGURATION
# =============================================================================

export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
CASE_SENSITIVE="true"

plugins=(
  git
  zsh-autosuggestions
  zsh-syntax-highlighting
)

source $ZSH/oh-my-zsh.sh
PROMPT='%F{yellow}%m%f %F{green}%n%f%F{magenta}:%~%F{magenta}$%f '
# =============================================================================
# 3. CUSTOM ALIASES
# =============================================================================

# Load custom aliases if file exists
if [ -f ~/.aliases ]; then
    source ~/.aliases
fi

# =============================================================================
# 4. GPG & YUBIKEY SSH-AGENT CONFIGURATION
# =============================================================================

# Export SSH socket globally
export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/ssh-agent.socket"

# Set GPG_TTY based on tty output to prevent 'not a tty' error
export GPG_TTY=$(tty)

# Start gpg-agent daemon if not running
if ! pgrep -x -u "$USER" gpg-agent >/dev/null; then
    gpg-agent --daemon >/dev/null 2>&1
fi

# Bind current TTY to agent
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1