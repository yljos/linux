#!/usr/bin/env bash

git config --global core.editor "vim"
git config --global user.signingkey CABB8B2144528A69
git config --global commit.gpgsign true
git config --global user.name "yljos"
git config --global user.email "yljos@ihuai.top"

systemctl --user daemon-reload
systemctl --user enable --now pipewire wireplumber ssh-agent >/dev/null 2>&1
curl -fLo ~/.vim/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

