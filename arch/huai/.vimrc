set number
set relativenumber
set showmode
set termguicolors
syntax on

call plug#begin('~/.vim/plugged')
Plug 'github/copilot.vim'
Plug 'psf/black'
call plug#end()

" Autocommands 
autocmd BufWritePre *.py Black
autocmd BufWritePre *.sh silent %!shfmt
" Disable mouse selection triggering visual mode
set mouse=

" Disable keys that enter visual mode
nnoremap v <Nop>
nnoremap V <Nop>
nnoremap <C-v> <Nop>
