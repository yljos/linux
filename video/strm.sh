#!/bin/bash

# Configuration
SRC_DIR="/data/www/media"
DEST_DIR="/data/media"
BASE_URL="http://10.0.0.21/media"

# 1. Generate or update strm files for mp4 only
find "$SRC_DIR" -type f -name "*.mp4" | while read -r file; do
    rel_path="${file#$SRC_DIR/}"
    strm_path="$DEST_DIR/${rel_path%.*}.strm"
    
    # Skip if strm is newer than source
    if [ "$strm_path" -nt "$file" ]; then
        continue
    fi

    # URL encode
    encoded_path=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$rel_path")
    
    mkdir -p "$(dirname "$strm_path")"
    echo "$BASE_URL/$encoded_path" > "$strm_path"
done

# 2. Cleanup orphaned strm files
find "$DEST_DIR" -type f -name "*.strm" | while read -r strm_file; do
    rel_path="${strm_file#$DEST_DIR/}"
    base_no_ext="${rel_path%.*}"
    
    # Remove strm if source mp4 is missing
    if [ ! -f "$SRC_DIR/$base_no_ext.mp4" ]; then
        rm "$strm_file"
    fi
done

# 3. Remove empty directories
find "$DEST_DIR" -type d -empty -delete