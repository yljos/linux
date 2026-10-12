import re
from pathlib import Path


# --- Helper Functions ---
def format_file_name(name):
    """
    File naming rules:
    - Has "_" -> My_Book
    - No "_" -> Mybook
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
    Recursively remove all nested/repeated prefixes including composite
    'Series - Vol. XX - ' patterns.
    """
    original = filename
    safe_prefix = re.escape(series_prefix) if series_prefix else ""

    if safe_prefix:
        # Match composite pattern first, then individual prefix components
        pattern = rf"^(?:{safe_prefix}\s*[-_]\s*(?:vol\.?|volume|v)\s*\d+[-_\s]+|{safe_prefix}[-_\s]+|(?:vol\.?|volume|v)\s*\d+[-_\s]+|\d+[-_\s]+)"
    else:
        pattern = r"^(?:(?:vol\.?|volume|v)\s*\d+[-_\s]+|\d+[-_\s]+)"

    while True:
        cleaned = re.sub(pattern, "", filename, count=1, flags=re.IGNORECASE)
        if cleaned == filename:
            break
        filename = cleaned

    if not Path(filename).stem:
        return original

    return filename


# --- Core Logic ---
def process_directory_recursively(current_dir, current_season=1):
    """
    Recursively process directory: traverse subfolders without renaming,
    then process .epub files in the current level.
    """
    print(f"--- Scanning: {current_dir} ---")

    try:
        all_items = list(current_dir.iterdir())
    except PermissionError:
        print(f"  [!] Permission denied, skipping: {current_dir}")
        return

    subdirs = sorted([x for x in all_items if x.is_dir()])
    files = sorted([x for x in all_items if x.is_file()])

    # --- Step 1: Recurse into subfolders (no renaming) ---
    folder_counter = 1
    for folder_path in subdirs:
        process_directory_recursively(folder_path, folder_counter)
        folder_counter += 1

    # --- Step 2: Process .epub files ---
    epub_files = [f for f in files if f.suffix.lower() == ".epub"]

    if not epub_files:
        return

    series_prefix = clean_foldername_prefix(current_dir.name)

    counter = 1
    for file_path in epub_files:
        original_name = file_path.name

        name_without_prefix = clean_filename_prefix(original_name, series_prefix)
        file_stem = Path(name_without_prefix).stem
        file_suffix = file_path.suffix

        cleaned_stem = format_file_name(file_stem)

        if not cleaned_stem:
            print(f"  Skipping: Main filename is empty '{original_name}'")
            continue

        # Format: Series - Vol. 01 - Title.epub
        new_filename = f"{series_prefix} - Vol. {counter:02d} - {cleaned_stem}{file_suffix}"
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