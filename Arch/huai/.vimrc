set number
set relativenumber
set showmode
set termguicolors
syntax on
function! SetManualGruvboxColors()
    " This ensures the settings are only applied when true color is available.
    if !&termguicolors
        return
    endif

    " --- Base Colors ---
    let s:foreground = '#ebdbb2'
    let s:background = 'NONE' " This is the key for transparency
    let s:comment    = '#928374'
    let s:red        = '#fb4934'
    let s:green      = '#b8bb26'
    let s:yellow     = '#fabd2f'
    let s:blue       = '#83a598'
    let s:purple     = '#d3869b'
    let s:aqua       = '#8ec07c'
    let s:orange     = '#fe8019'
    let s:bg1        = '#3c3836' " A dark grey for UI elements

    " Reset all syntax highlighting to a clean slate
    highlight clear

    " --- Set the main editor appearance ---
    " guibg=NONE makes the background transparent
    execute 'highlight Normal guifg=' . s:foreground . ' guibg=' . s:background
    execute 'highlight NonText guifg=' . s:comment . ' guibg=' . s:background

    " --- Common Syntax Groups ---
    execute 'highlight Comment    guifg=' . s:comment
    execute 'highlight Constant   guifg=' . s:purple
    execute 'highlight String     guifg=' . s:green
    execute 'highlight Character  guifg=' . s:green
    execute 'highlight Number     guifg=' . s:purple
    execute 'highlight Boolean    guifg=' . s:purple
    execute 'highlight Identifier guifg=' . s:blue
    execute 'highlight Function   guifg=' . s:yellow
    execute 'highlight Statement  guifg=' . s:red
    execute 'highlight Operator   guifg=' . s:red
    execute 'highlight Keyword    guifg=' . s:red
    execute 'highlight PreProc    guifg=' . s:aqua
    execute 'highlight Type       guifg=' . s:yellow
    execute 'highlight Special    guifg=' . s:orange

    " --- UI Elements ---
    execute 'highlight LineNr     guifg=' . s:comment    . ' guibg=' . s:background
    execute 'highlight CursorLine guibg=' . s:bg1
    execute 'highlight Visual     guibg=' . s:bg1
endfunction

call SetManualGruvboxColors()


call plug#begin('~/.vim/plugged')
Plug 'github/copilot.vim'
Plug 'psf/black'
call plug#end()

" Autocommands 
autocmd BufWritePre *.py Black
autocmd BufWritePre *.sh silent %!shfmt
