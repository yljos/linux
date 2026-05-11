#!/usr/bin/env bash

rsync -r root/ /root/
rsync -r etc/ /etc/

find /root/.ssh -type d -exec chmod 700 {} +
find /root/.ssh -type f -exec chmod 600 {} +

