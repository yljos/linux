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

# --- Core Logic ---
def clean_foldername_prefix(foldername):
    """
    Remove existing '01_' or 'S01_' prefixes from the foldername
    Returns the foldername string without the prefix to prevent S01_S01_
    """
    try:
        if "_" in foldername:
            prefix, rest = foldername.split("_", 1)
            # Check if it is purely numeric (e.g. 01)
            is_digit_prefix = prefix.isdigit()
            # Check if it is S + number (e.g. S01)
            is_season_prefix = prefix.startswith("S") and prefix[1:].isdigit()

            if is_digit_prefix or is_season_prefix:
                return rest
    except ValueError:
        pass
    return foldername

def clean_filename_prefix(filename):
    """
    Remove existing '01_' or 'E01_' prefixes from the filename
    Returns the filename string without the prefix
    """
    try:
        if "_" in filename:
            prefix, rest = filename.split("_", 1)
            # Check if it is purely numeric (e.g. 01)
            is_digit_prefix = prefix.isdigit()
            # Check if it is E + number (e.g. E01)
            is_episode_prefix = prefix.startswith("E") and prefix[1:].isdigit()

            if is_digit_prefix or is_episode_prefix:
                return rest
    except ValueError:
        pass
    return filename

def process_directory_recursively(current_dir):
    """
    Recursively process directory: process folders in current level first (rename and recurse),
    then process files in the current level.
    """
    print(f"--- Scanning: {current_dir} ---")

    # Get all contents in current directory and convert to fixed list
    try:
        all_items = list(current_dir.iterdir())
    except PermissionError:
        print(f" [!] Permission denied, skipping: {current_dir}")
        return

    # Categorize and sort
    subdirs = sorted([x for x in all_items if x.is_dir()])
    files = sorted([x for x in all_items if x.is_file()])

    # --- Step 1: Process subfolders (rename + recurse) ---
    folder_counter = 1
    for folder_path in subdirs:
        old_name = folder_path.name
        
        # 1. Clean existing prefix to prevent S01_S01_
        name_without_prefix = clean_foldername_prefix(old_name)
            
        # 2. Combine new folder name with Sxx_ prefix (keeping original name intact)
        new_name = f"S{folder_counter:02d}_{name_without_prefix}"

        if old_name != new_name:
            new_folder_path = folder_path.with_name(new_name)
            try:
                folder_path.rename(new_folder_path)
                print(f"  [Folder] Renamed: '{old_name}' -> '{new_name}'")
                folder_path = new_folder_path
            except OSError as e:
                print(f"  [!] Folder rename failed '{old_name}': {e}")

        folder_counter += 1
        process_directory_recursively(folder_path)

    # --- Step 2: Process .mp4 files ---
    mp4_files = [f for f in files if f.suffix.lower() == ".mp4"]

    if not mp4_files:
        return

    counter = 1
    for file_path in mp4_files:
        original_name = file_path.name

        # 1. Clean prefix
        name_without_prefix = clean_filename_prefix(original_name)

        # 2. Separate filename and suffix
        file_stem = Path(name_without_prefix).stem
        file_suffix = file_path.suffix

        # 3. Format main filename
        cleaned_stem = format_file_name(file_stem)

        if not cleaned_stem:
            print(f"  Skipping: Main filename is empty '{original_name}'")
            continue

        # 4. Combine new filename
        new_filename = f"E{counter:02d}_{cleaned_stem}{file_suffix}"
        new_file_path = file_path.with_name(new_filename)

        # 5. Execute rename
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
    # Get current working directory
    root_path = Path.cwd()

    print(f"Start processing root directory: {root_path}\n")
    process_directory_recursively(root_path)
    print("\nProcessing complete!")