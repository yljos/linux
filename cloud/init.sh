#!/usr/bin/env bash

rsync -r root/ /root/
find /root/.ssh /home/huai/.gnupg -type d -exec chmod 700 {} +
find /root/.ssh /home/huai/.gnupg -type f -exec chmod 600 {} +

