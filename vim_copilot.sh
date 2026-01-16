#!/usr/bin/env bash

echo "=== Starting Vim Copilot Environment Setup ==="

echo "Downloading and installing vim-plug plugin manager..."
curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
	https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
echo "vim-plug installation completed!"

echo "Downloading and installing GitHub Copilot.vim plugin..."
git clone --depth=1 https://github.com/github/copilot.vim.git \
	~/.vim/pack/github/start/copilot.vim
echo "GitHub Copilot plugin installation completed!"
echo "=== Vim Copilot Environment Setup Completed ==="
echo "Usage:"
echo "1. Launch Vim and run :Copilot setup for authorization"
echo "2. Follow the prompts to complete GitHub authentication"
echo "3. Restart Vim to use Copilot features"
