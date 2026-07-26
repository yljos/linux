#!/usr/bin/env bash

git config --global core.editor "vim"
git config --global user.signingkey 4005DCF7C751DCD3257FBD13D74AA1C746C47427
git config --global commit.gpgsign true
git config --global user.name "yljos"
git config --global user.email "git@sakuraos.com"
git config --global core.sshCommand "C:/Windows/System32/OpenSSH/ssh.exe"

Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
