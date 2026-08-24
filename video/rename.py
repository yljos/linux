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

def clean_filename_prefix(filename):
    """
    Recursively remove all nested/repeated prefixes 
    (e.g., 'Ai_s01e01_', 'Mv_S01e05_', 'E01_', '01_')
    """
    original = filename
    # Matches any prefix ending with sXXeYY_ OR matches E01_ / 01_
    pattern = r'^(?:.*?s\d+e\d+_|[eE]?\d+_)'
    
    # Loop to peel off multiple nested prefixes layer by layer
    while True:
        cleaned = re.sub(pattern, '', filename, count=1, flags=re.IGNORECASE)
        if cleaned == filename:
            break
        filename = cleaned
        
    # Keep original if stripping results in an empty stem
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
        new_name = f"S{folder_counter:02d}_{name_without_prefix}"

        if old_name != new_name:
            new_folder_path = folder_path.with_name(new_name)
            try:
                folder_path.rename(new_folder_path)
                print(f"  [Folder] Renamed: '{old_name}' -> '{new_name}'")
                folder_path = new_folder_path
            except OSError as e:
                print(f"  [!] Folder rename failed '{old_name}': {e}")

        # Recurse into subdirectories, passing down the folder_counter as the season number
        process_directory_recursively(folder_path, folder_counter)
        folder_counter += 1

    # --- Step 2: Process .mp4 files ---
    mp4_files = [f for f in files if f.suffix.lower() == ".mp4"]

    if not mp4_files:
        return

    # Extract series prefix dynamically from the current folder name (e.g., 'S01_Ai' -> 'Ai')
    series_prefix = clean_foldername_prefix(current_dir.name)

    counter = 1
    for file_path in mp4_files:
        original_name = file_path.name

        name_without_prefix = clean_filename_prefix(original_name)
        file_stem = Path(name_without_prefix).stem
        file_suffix = file_path.suffix
        
        cleaned_stem = format_file_name(file_stem)

        if not cleaned_stem:
            print(f"  Skipping: Main filename is empty '{original_name}'")
            continue

        # Combine new filename (e.g., Ai_s01e05_Title.mp4)
        new_filename = f"{series_prefix}_s{current_season:02d}e{counter:02d}_{cleaned_stem}{file_suffix}"
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