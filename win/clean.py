import os
import json
import subprocess
import re

# Target remote path
REMOTE_PATH = "pikpak:My Pack"

# Regex to match suffix like "(1)", " (2)", etc., at the end of the filename stem
SUFFIX_RE = re.compile(r'\s*\(\d+\)$')

def main():
    # Fetch remote file tree
    cmd = ["rclone", "lsjson", REMOTE_PATH, "--recursive", "--files-only"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    
    if result.returncode != 0:
        return

    try:
        remote_files = json.loads(result.stdout)
    except json.JSONDecodeError:
        return

    # Dictionary to group files
    # Format: {(size, normalized_name): [list_of_paths]}
    file_groups = {}

    # Process files to group them by exact size and normalized name
    for item in remote_files:
        rel_path = item["Path"]
        name = item["Name"]
        file_size = item.get("Size", 0)
        
        # Split extension and stem
        stem, ext = os.path.splitext(name)
        
        # Remove suffix like (1) or (2) from the stem to get the normalized base name
        norm_stem = SUFFIX_RE.sub('', stem)
        norm_name = norm_stem + ext.lower()
        
        # Group key: exact size + normalized file name
        group_key = (file_size, norm_name)
        
        if group_key not in file_groups:
            file_groups[group_key] = []
        file_groups[group_key].append(rel_path)

    files_to_del = []

    # Find duplicates within the groups
    for group_key, paths in file_groups.items():
        if len(paths) > 1:
            # Sort paths by the length of the filename
            # The original file without "(1)" will have a shorter name length
            paths.sort(key=lambda p: len(os.path.basename(p)))
            
            # Keep the first one (shortest name, original), mark the rest for deletion
            files_to_del.extend(paths[1:])

    # Execute deletions via stdin
    if files_to_del:
        files_to_del = list(set(files_to_del))
        delete_payload = "\n".join(files_to_del)
        
        subprocess.run(
            ["rclone", "delete", REMOTE_PATH, "--files-from", "-"],
            input=delete_payload,
            text=True,
            encoding="utf-8"
        )

    # Clean up empty directories
    subprocess.run(["rclone", "rmdirs", REMOTE_PATH, "--leave-root"])

if __name__ == "__main__":
    main()