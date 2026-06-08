# =============================================================================
# 1. EARLY INITIALIZATION (Must stay at the top)
# =============================================================================

# Enable Powerlevel10k instant prompt
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# =============================================================================
# 2. ENVIRONMENT & EDITOR SETTINGS
# =============================================================================

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export VISUAL=vim
export EDITOR=vim
export TERM=xterm-256color 

# =============================================================================
# 3. OH MY ZSH CONFIGURATION
# =============================================================================

export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="powerlevel10k/powerlevel10k"
CASE_SENSITIVE="true"

plugins=(
  git
  zsh-autosuggestions
  zsh-syntax-highlighting
)

source $ZSH/oh-my-zsh.sh

# =============================================================================
# 4. CUSTOM ALIASES
# =============================================================================

# Load custom aliases if file exists
if [ -f ~/.aliases ]; then
    source ~/.aliases
fi

# =============================================================================
# 5. GPG & YUBIKEY SSH-AGENT CONFIGURATION
# =============================================================================

# Export SSH socket globally
export SSH_AUTH_SOCK="$(gpgconf --list-dirs agent-ssh-socket)"

# Set GPG_TTY based on tty output to prevent 'not a tty' error
_RAW_TTY=$(tty 2>/dev/null)
if [[ "$_RAW_TTY" != "not a tty" ]]; then
    export GPG_TTY=$_RAW_TTY
else
    export GPG_TTY=$TTY
fi
unset _RAW_TTY


# Start gpg-agent daemon if not running
if ! pgrep -x -u "$USER" gpg-agent >/dev/null; then
    gpg-agent --daemon >/dev/null 2>&1
fi

# Bind current TTY to agent
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1

# =============================================================================
# 6. LATE INITIALIZATION (Must stay at the bottom)
# =============================================================================

# Load Powerlevel10k theme configuration
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh