set number
syntax on
set termguicolors
set showmode
set relativenumber
call plug#begin('~/.vim/plugged')

" GitHub Copilot 插件
Plug 'github/copilot.vim'
" Python 代码格式化工具 Black
Plug 'psf/black'

call plug#end()
" 自动格式化 Python 代码
autocmd BufWritePre *.py Black
" 自动格式化 Shell 脚本
autocmd BufWritePre *.sh silent %!shfmt
