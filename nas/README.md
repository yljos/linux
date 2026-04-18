# Debian NAS Notes

## RAID 1 Setup & Configuration Run as root

### 1. Install mdadm
 
```bash
apt update && apt install mdadm -y
```

### 2. Check Devices
```bash
fdisk -l
```

### 3. Disk Preparation
# Zero existing superblocks to prevent conflicts
```bash
mdadm --zero-superblock /dev/sdb /dev/sdc
```

### 4. Array Creation
# Create RAID 1 array
```bash
mdadm --create --verbose /dev/md0 --level=1 --raid-devices=2 /dev/sdb /dev/sdc

# Verify array status
cat /proc/mdstat
```

### 5. Format & Mount
# Format the new RAID device
```bash
mkfs.ext4 /dev/md0
```

# Create mount point and mount FIRST
```bash
mkdir -p /data
mount /dev/md0 /data
```

# Set permissions and ownership AFTER mounting
```bash
chmod 755 -R /data
chown huai:huai -R /data
```

### 6. Persistence Configuration
# Save mdadm config for boot persistence
```bash
mdadm --detail --scan >> /etc/mdadm/mdadm.conf
update-initramfs -u
```

# Get UUID for fstab
```bash
blkid /dev/md0
```

# Configure auto-mount
```bash
vim /etc/fstab
# Append the following line (replace <UUID> with actual output):
# UUID=<UUID> /data ext4 defaults 0 0
```