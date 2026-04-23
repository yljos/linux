```bash
sudo efibootmgr --create --disk /dev/mmcblk0 --part 1 --label "Nas" \
    --loader /EFI/nas/vmlinuz \
    --unicode "root=UUID=18a054b2-1e9c-4b1d-8a48-fd20fa59c833 ro quiet loglevel=3 vt.global_cursor_default=0 initrd=/EFI/nas/initrd.img"
```    