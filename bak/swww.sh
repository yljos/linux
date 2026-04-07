#!/usr/bin/dash

PICTURE_DIR="$HOME/Pictures"
FILES_CACHE="/tmp/wallpaper_files"
INDEX_FILE="/tmp/wallpaper_index"

# 如果缓存不存在或为空，扫描目录一次
if [ ! -f "$FILES_CACHE" ] || [ ! -s "$FILES_CACHE" ]; then
	i=0
	>"$FILES_CACHE" # 清空文件
	for f in "$PICTURE_DIR"/*; do
		[ -f "$f" ] || continue
		echo "$f" >>"$FILES_CACHE"
		i=$((i + 1))
	done
fi

# 读取文件数量
COUNT=$(wc -l <"$FILES_CACHE")
[ "$COUNT" -eq 0 ] && exit 0

# 读取上次索引
if [ -f "$INDEX_FILE" ]; then
	INDEX=$(cat "$INDEX_FILE")
else
	INDEX=0
fi

# 获取当前图片
PIC=$(sed -n "$((INDEX + 1))p" "$FILES_CACHE")

# 设置壁纸
swww img --transition-type random "$PIC" -n 0

# 更新索引，循环到头
INDEX=$(((INDEX + 1) % COUNT))
echo "$INDEX" >"$INDEX_FILE"
