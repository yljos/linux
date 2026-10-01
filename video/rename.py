import re
from pathlib import Path

# --- Helper Functions ---
def format_file_name(name):
    """
    File naming rules:
    - Has "_" -> My_Video
    - No "_" -> Myvideo
    """
    if "_" in name:
        parts = name.split("_")
        capitalized_parts = [p.capitalize() for p in parts if p]
        return "_".join(capitalized_parts)
    else:
        return name.capitalize()

def clean_foldername_prefix(foldername):
    """
    Remove existing '01_' or 'S01_' prefixes from the foldername
    """
    try:
        if "_" in foldername:
            prefix, rest = foldername.split("_", 1)
            is_digit_prefix = prefix.isdigit()
            is_season_prefix = prefix.upper().startswith("S") and prefix[1:].isdigit()

            if is_digit_prefix or is_season_prefix:
                return rest
    except ValueError:
        pass
    return foldername

def clean_filename_prefix(filename, series_prefix=""):
    """
    Recursively remove all nested/repeated prefixes using either '_' or '-'
    (e.g., 'Ai_s01e01_', '01-ai-', '01_Ai_', 'E01_')
    """
    original = filename
    safe_prefix = re.escape(series_prefix) if series_prefix else ""
    
    # Match sXXeYY patterns, the '01_prefix_' / '01-prefix-' patterns, and generic '01_' / 'E01_'
    if safe_prefix:
        pattern = rf'^(?:.*?s\d+e\d+[-_]+|\d+[-_]+{safe_prefix}[-_]+|[eE]?\d+[-_]+)'
    else:
        pattern = r'^(?:.*?s\d+e\d+[-_]+|[eE]?\d+[-_]+)'
    
    while True:
        # re.IGNORECASE will handle both 'Ai' and 'ai'
        cleaned = re.sub(pattern, '', filename, count=1, flags=re.IGNORECASE)
        if cleaned == filename:
            break
        filename = cleaned
        
    if not Path(filename).stem:
        return original
        
    return filename

# --- Core Logic ---
def process_directory_recursively(current_dir, current_season=1):
    """
    Recursively process directory: process folders in current level first,
    then process files in the current level.
    """
    print(f"--- Scanning: {current_dir} ---")

    try:
        all_items = list(current_dir.iterdir())
    except PermissionError:
        print(f" [!] Permission denied, skipping: {current_dir}")
        return

    subdirs = sorted([x for x in all_items if x.is_dir()])
    files = sorted([x for x in all_items if x.is_file()])

    # --- Step 1: Process subfolders (rename + recurse) ---
    folder_counter = 1
    for folder_path in subdirs:
        old_name = folder_path.name
        name_without_prefix = clean_foldername_prefix(old_name)
        
        # Format: 01_foldername
        new_name = f"{folder_counter:02d}_{name_without_prefix}"

        if old_name != new_name:
            new_folder_path = folder_path.with_name(new_name)
            try:
                folder_path.rename(new_folder_path)
                print(f"  [Folder] Renamed: '{old_name}' -> '{new_name}'")
                folder_path = new_folder_path
            except OSError as e:
                print(f"  [!] Folder rename failed '{old_name}': {e}")

        process_directory_recursively(folder_path, folder_counter)
        folder_counter += 1

    # --- Step 2: Process .mp4 files ---
    mp4_files = [f for f in files if f.suffix.lower() == ".mp4"]

    if not mp4_files:
        return

    series_prefix = clean_foldername_prefix(current_dir.name)

    counter = 1
    for file_path in mp4_files:
        original_name = file_path.name

        # Pass series_prefix to accurately clean hybrid formats like '01-ai-' and '01_Ai_'
        name_without_prefix = clean_filename_prefix(original_name, series_prefix)
        file_stem = Path(name_without_prefix).stem
        file_suffix = file_path.suffix
        
        cleaned_stem = format_file_name(file_stem)

        if not cleaned_stem:
            print(f"  Skipping: Main filename is empty '{original_name}'")
            continue

        # Format: 01_anything_title.mp4
        new_filename = f"{counter:02d}_{series_prefix}_{cleaned_stem}{file_suffix}"
        new_file_path = file_path.with_name(new_filename)

        if file_path != new_file_path:
            try:
                file_path.rename(new_file_path)
                print(f"  [File] Renamed: '{original_name}' -> '{new_filename}'")
            except OSError as e:
                print(f"  [!] File rename failed '{original_name}': {e}")
        else:
            print(f"  [File] No change needed: '{original_name}'")

        counter += 1

if __name__ == "__main__":
    root_path = Path.cwd()
    print(f"Start processing root directory: {root_path}\n")
    process_directory_recursively(root_path)
    print("\nProcessing complete!")