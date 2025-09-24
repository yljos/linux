# Firejail profile for zen-browser
# Description: Fast, private, and secure web browser based on Firefox
# This file is overwritten after every install/update
# Persistent local customizations
include zen-browser.local
# Persistent global definitions
include globals.local

# Note: Sandboxing web browsers is as important as it is complex. Users might
# be interested in creating custom profiles depending on the use case (e.g. one
# for general browsing, another for banking, ...). Consult our FAQ/issue
# tracker for more information. Here are a few links to get you going:
# https://github.com/netblue30/firejail/wiki/Frequently-Asked-Questions#firefox-doesnt-open-in-a-new-sandbox-instead-it-opens-a-new-tab-in-an-existing-firefox-instance
# https://github.com/netblue30/firejail/wiki/Frequently-Asked-Questions#how-do-i-run-two-instances-of-firefox
# https://github.com/netblue30/firejail/issues/4206#issuecomment-824806968

# (Ignore entry from disable-common.inc)
ignore read-only ${HOME}/.zen/profiles.ini

noblacklist ${HOME}/.cache/zen
noblacklist ${HOME}/.zen
noblacklist ${HOME}/Downloads
noblacklist ${RUNUSER}/*zen*
noblacklist ${RUNUSER}/psd/*zen*

# Security: Block access to sensitive directories
blacklist /usr/libexec

mkdir ${HOME}/.cache/zen  
mkdir ${HOME}/.zen
mkdir ${HOME}/Downloads
whitelist ${HOME}/.cache/zen
whitelist ${HOME}/.zen
whitelist ${HOME}/Downloads
whitelist ${RUNUSER}/*zen*
whitelist ${RUNUSER}/psd/*zen*

# Note: Firefox requires a shell to launch on Arch and Fedora.
# Add the next lines to zen-browser.local to enable private-bin.
#private-bin bash,dbus-launch,dbus-send,env,zen-browser,sh,which
#private-bin basename,bash,cat,dirname,expr,false,zen-browser,zen-browser-wayland,getenforce,ln,mkdir,pidof,restorecon,rm,rmdir,sed,sh,tclsh,true,uname
private-etc zen-browser

dbus-user filter
dbus-user.own org.mozilla.*
dbus-user.own org.mpris.MediaPlayer2.firefox.*
ignore dbus-user none

# Custom configuration for zen-browser only
# Do not include firefox-common.profile to avoid security bypass
include firefox-common.profile