#!/usr/bin/env bash

# --- [1] Data Synchronization ---
# Sync user-specific text configurations
rsync -r huai/ /home/huai/

# Sync system-wide configurations if the source directory exists
if [[ -d "etc" ]]; then
    rsync -r etc/ /etc/
fi

# --- [2] Ownership & Permissions ---
# Ensure the user 'huai' owns their home directory after rsync
chown huai:huai -R /home/huai/

# Apply strict permissions for SSH and GPG
# Directories: 700 (drwx------) | Files: 600 (-rw-------)
find /home/huai/.ssh /home/huai/.gnupg -type d -exec chmod 700 {} + 2>/dev/null
find /home/huai/.ssh /home/huai/.gnupg -type f -exec chmod 600 {} + 2>/dev/null

# --- [3] Security Keys ---
# Import the GPG public key for user 'huai' specifically
# This prevents importing into the root keyring
curl -sL "http://10.0.0.21/key/yljos_pub.asc" | sudo -u huai gpg --import >/dev/null 2>&1

# --- [4] Systemd User Services ---
# Bridge to the user's D-Bus session for service management
export XDG_RUNTIME_DIR="/run/user/$(id -u huai)"

# Reload and enable user services as the 'huai' user
sudo -u huai systemctl --user daemon-reload
sudo -u huai systemctl --user enable --now pipewire wireplumber shutdown >/dev/null 2>&1

# --- [5] Cleanup/Overwrites ---
# Overwrite Kerberos config to disable/clear existing settings
tee /etc/krb5.conf </dev/null

echo "Arch Linux initialization complete."