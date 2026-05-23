# Arch Linux NAS Notes

## RAID 1 Setup & Configuration (Run as root)

### 1. Check Devices
```bash
lsblk
```

### 2. Disk Preparation 
```bash
mdadm --zero-superblock /dev/sdb /dev/sdc
```

### 3. Array Creation
```bash
mdadm --assemble --scan
# Create RAID 1 array
mdadm --create --verbose /dev/md0 --level=1 --raid-devices=2 /dev/sdb /dev/sdc

# Verify array status
cat /proc/mdstat
```

### 4. Format & Mount
```bash
mkfs.ext4 /dev/md0
mount /dev/md0 /data
```

### 5. Persistence Configuration
```bash
# Save mdadm config
mdadm --detail --scan >> /etc/mdadm.conf
```

### 6. fstab Configuration
```bash
blkid /dev/md0

vim /etc/fstab
# Append the following line (replace <UUID> with actual output):
# UUID=<UUID> /data ext4 defaults 0 0
# UUID=<UUID> /podman xfs defaults 0 0
```

### 7. Services & Samba Configuration
```bash
# Enable and start NFS and Samba services
systemctl enable --now nfs-server
systemctl enable --now smb 

# Add and enable Samba user
smbpasswd -a huai
smbpasswd -e huai
```

