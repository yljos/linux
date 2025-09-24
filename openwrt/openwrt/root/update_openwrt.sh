#!/usr/bin/env bash
opkg update && opkg upgrade $(opkg list-upgradable | awk '{print $1}')
