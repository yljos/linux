#!/usr/bin/env bash

git config --global core.editor "vim"
git config --global user.signingkey 4005DCF7C751DCD3257FBD13D74AA1C746C47427
git config --global commit.gpgsign true
git config --global user.name "yljos"
git config --global user.email "git@sakuraos.com"

systemctl --user daemon-reload
systemctl --user enable --now pipewire wireplumber ssh-agent >/dev/null 2>&1
curl -fLo ~/.vim/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
