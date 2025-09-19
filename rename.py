import os
import re  # 导入正则表达式模块

def format_folder_name(name):
    """
    辅助函数：应用文件夹的命名规则。
    - 有"_" -> My_Folder
    - 无"_" -> MYFOLDER
    """
    if "_" in name:
        parts = name.split('_')
        capitalized_parts = [p.capitalize() for p in parts if p]
        return "_".join(capitalized_parts)
    else:
        cleaned_name = re.sub(r'[^a-zA-Z0-9]+', '', name)
        return cleaned_name.upper()

def format_file_name(name):
    """
    辅助函数：应用.webm文件的命名规则。
    - 有"_" -> My_Video
    - 无"_" -> Myvideo
    """
    if "_" in name:
        parts = name.split('_')
        capitalized_parts = [p.capitalize() for p in parts if p]
        return "_".join(capitalized_parts)
    else:
        return name.capitalize()


def smart_rename_all(root_directory):
    """
    (文件夹与文件规则分离最终版)
    对文件夹和.webm文件应用两套不同的重命名逻辑。
    """
    abs_root = os.path.abspath(root_directory)
    print(f"开始处理根目录： {abs_root}\n")

    for dirpath, dirnames, filenames in os.walk(root_directory, topdown=True):
        print(f"--- 正在处理文件夹: {dirpath} ---")

        # --- 第一步: 应用【文件夹规则】重命名子文件夹 ---
        for i, dirname in enumerate(dirnames):
            cleaned_dirname = format_folder_name(dirname)
            
            if dirname != cleaned_dirname and cleaned_dirname:
                old_dir_path = os.path.join(dirpath, dirname)
                new_dir_path = os.path.join(dirpath, cleaned_dirname)
                
                try:
                    os.rename(old_dir_path, new_dir_path)
                    print(f"  [文件夹] 已重命名: '{dirname}' -> '{cleaned_dirname}'")
                    dirnames[i] = cleaned_dirname
                except OSError as e:
                    print(f"  错误：重命名文件夹 '{dirname}' 时出错: {e}")

        # --- 第二步: 应用【文件规则】处理.webm文件 ---
        counter = 1
        webm_files = sorted([f for f in filenames if f.lower().endswith(".webm")])

        if not webm_files:
            continue

        for filename in webm_files:
            base_filename = filename
            
            try:
                prefix, rest_of_name = filename.split("_", 1)
                is_old_prefix = prefix.isdigit()
                is_new_prefix = prefix.startswith("E") and prefix[1:].isdigit()
                if is_old_prefix or is_new_prefix:
                    base_filename = rest_of_name
            except ValueError:
                pass

            old_file_path = os.path.join(dirpath, filename)
            
            name_part, extension = os.path.splitext(base_filename)
            
            cleaned_name_part = format_file_name(name_part)
            
            if not cleaned_name_part:
                print(f"  跳过：'{filename}' 的文件名部分在清理后为空。")
                continue

            cleaned_base_filename = cleaned_name_part + extension
            
            new_filename = f"E{counter:02d}_{cleaned_base_filename}"
            new_file_path = os.path.join(dirpath, new_filename)

            if old_file_path != new_file_path:
                try:
                    os.rename(old_file_path, new_file_path)
                    print(f"  [文件] 已重命名: '{filename}' -> '{new_filename}'")
                except OSError as e:
                    print(f"  错误：重命名文件 '{filename}' 时出错: {e}")
            else:
                print(f"  [文件] '{filename}' 无需更改。")
            
            counter += 1

    print("\n处理完成！")


if __name__ == "__main__":
    directory_to_process = "."
    smart_rename_all(directory_to_process)