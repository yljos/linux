#!/usr/bin/env bash

rsync -r huai/ ~/
# Fix directory permissions
chmod 700 ~/.ssh ~/.gnupg

# Fix file permissions
chmod 600 ~/.ssh/* ~/.gnupg/*
