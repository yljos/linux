#!/usr/bin/env bash

rsync -r huai/ /home/huai/

# Fix directory permissions
chown huai:huai -R /home/huai/

# Fix file permissions
find /home/huai/.ssh /home/huai/.gnupg -type d -exec chmod 700 {} +
find /home/huai/.ssh /home/huai/.gnupg -type f -exec chmod 600 {} +

# git
git config --global core.editor "vim"
git config --global user.signingkey CABB8B2144528A69
git config --global commit.gpgsign true
git config --global user.name "yljos"
git config --global user.email "yljos@ihuai.top"

curl -s "http://10.0.0.21/key/20260429_pub.asc" | gpg --import >/dev/null 2>&1

# vim
curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
	https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
