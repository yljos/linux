
if [ -f "${HOME}/.bashrc" ] ; then
  source "${HOME}/.bashrc"
fi
cd /home/huai/linux

if [ "$(tty)" = "/dev/pty0" ]; then
    codium .
    exit
fi