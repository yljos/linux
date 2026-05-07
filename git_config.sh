#!/usr/bin/env bash
git config --global core.editor "vim"
git config --global user.signingkey CABB8B2144528A69
git config --global commit.gpgsign true
git config --global user.name "yljos"
git config --global user.email "yljos@ihuai.top"

curl -s "http://10.0.0.21/key/20260429_pub.asc" | gpg --import >/dev/null 2>&1
