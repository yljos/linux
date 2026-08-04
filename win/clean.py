import os
import json
import subprocess
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
env_blacklist = os.getenv("BLACKLIST_MP4", "")
BLACKLIST_MP4 = {name.strip() for name in env_blacklist.split(",") if name.strip()}
WHITELIST_EXT = {".mkv", ".avi", ".mov", ".wmv", ".ts"}

REMOTE_PATH = "pikpak:My Pack"

# 20MB threshold in bytes
MIN_MP4_SIZE_BYTES = 20 * 1024 * 1024

# Regex to match suffix like "(1)", " (2)", etc., at the end of the filename stem
SUFFIX_RE = re.compile(r"\s*\(\d+\)$")


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

    files_to_del = set()
    file_groups = {}

    # Process files
    for item in remote_files:
        rel_path = item["Path"]
        name = item["Name"]
        file_size = item.get("Size", 0)

        base_name, ext = os.path.splitext(name)
        ext_lower = ext.lower()

        keep_file = True

        # Apply whitelist, blacklist, and size logic
        if ext_lower not in WHITELIST_EXT:
            if ext_lower == ".mp4":
                if (
                    any(b in base_name for b in BLACKLIST_MP4)
                    or file_size < MIN_MP4_SIZE_BYTES
                ):
                    files_to_del.add(rel_path)
                    keep_file = False
            else:
                files_to_del.add(rel_path)
                keep_file = False

        # Group valid files for duplicate detection
        if keep_file:
            norm_stem = SUFFIX_RE.sub("", base_name)
            norm_name = norm_stem + ext_lower
            group_key = (file_size, norm_name)

            if group_key not in file_groups:
                file_groups[group_key] = []
            file_groups[group_key].append(rel_path)

    # Process duplicates
    for group_key, paths in file_groups.items():
        if len(paths) > 1:
            # Sort paths by filename length to keep the shortest (original)
            paths.sort(key=lambda p: len(os.path.basename(p)))
            for p in paths[1:]:
                files_to_del.add(p)

    # Execute deletions via stdin (no temporary file)
    if files_to_del:
        delete_payload = "\n".join(files_to_del)
        subprocess.run(
            ["rclone", "delete", REMOTE_PATH, "--files-from", "-"],
            input=delete_payload,
            text=True,
            encoding="utf-8",
        )

    # Clean up empty directories
    subprocess.run(["rclone", "rmdirs", REMOTE_PATH, "--leave-root"])


if __name__ == "__main__":
    main()
