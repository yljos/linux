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
```bash
mdadm --zero-superblock /dev/sdb /dev/sdc
```

### 4. Array Creation Create RAID 1 array

```bash
mdadm --create --verbose /dev/md0 --level=1 --raid-devices=2 /dev/sdb /dev/sdc

# Verify array status
cat /proc/mdstat
```

### 5. Format & Mount
```bash
mkfs.ext4 /dev/md0
```

```bash
mkdir -p /data
mount /dev/md0 /data
```

```bash
chmod 755 -R /data
chown huai:huai -R /data
```

### 6. Persistence Configuration
```bash
mdadm --detail --scan >> /etc/mdadm/mdadm.conf
update-initramfs -u
```

```bash
blkid /dev/md0
```

```bash
vim /etc/fstab
# Append the following line (replace <UUID> with actual output):
# UUID=<UUID> /data ext4 defaults 0 0
```

sudo xbps-install -S catatonit