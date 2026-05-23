# Void Linux NAS Notes

## RAID 1 Setup & Configuration (Run as root)

### 1. Install mdadm
```bash
xbps-install -Su mdadm
```

### 2. Check Devices
```bash
lsblk
```

### 3. Disk Preparation 
```bash
mdadm --zero-superblock /dev/sdb /dev/sdc
```

### 4. Array Creation
```bash
mdadm --assemble --scan
# Create RAID 1 array
mdadm --create --verbose /dev/md0 --level=1 --raid-devices=2 /dev/sdb /dev/sdc

# Verify array status
cat /proc/mdstat
```

### 5. Format & Mount
```bash
mkfs.ext4 /dev/md0
mkdir -p /data
mount /dev/md0 /data
chmod 755 -R /data
```

### 6. Persistence Configuration
```bash
# Save mdadm config
mdadm --detail --scan >> /etc/mdadm.conf

# Update initramfs for Void Linux
xbps-reconfigure -a
```

### 7. fstab Configuration
```bash
blkid /dev/md0

vim /etc/fstab
# Append the following line (replace <UUID> with actual output):
# UUID=<UUID> /data ext4 defaults 0 0
```

### 8. Additional Packages
```bash
xbps-install -S catatonit
```