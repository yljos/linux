import re
from pathlib import Path
import sys  # 新增导入
import time  # 新增导入

# --- 配置区 (新增) ---
# 工作指示文件路径配置 (与 mp4_to_webm.py 保持一致)
WORKING_FILE_PATH = Path(r"C:\shutdown\working")
CHECK_INTERVAL_SECONDS = 10  # 检查 working 文件的间隔时间
# --- 配置区结束 ---


# --- 辅助函数 (保持原有逻辑) ---
def format_folder_name(name):
    """
    文件夹命名规则：
    - 有"_" -> My_Folder
    - 无"_" -> MYFOLDER
    """
    if "_" in name:
        parts = name.split("_")
        capitalized_parts = [p.capitalize() for p in parts if p]
        return "_".join(capitalized_parts)
    else:
        cleaned_name = re.sub(r"[^a-zA-Z0-9]+", "", name)
        return cleaned_name.upper()


def format_file_name(name):
    """
    文件命名规则：
    - 有"_" -> My_Video
    - 无"_" -> Myvideo
    """
    if "_" in name:
        parts = name.split("_")
        capitalized_parts = [p.capitalize() for p in parts if p]
        return "_".join(capitalized_parts)
    else:
        return name.capitalize()


# --- 核心逻辑 (Pathlib 重构版) ---


def clean_filename_prefix(filename):
    """
    移除文件名中已有的 '01_' 或 'E01_' 前缀
    返回去除前缀后的文件名字符串
    """
    try:
        if "_" in filename:
            prefix, rest = filename.split("_", 1)
            # 检查是否是纯数字 (例如 01)
            is_digit_prefix = prefix.isdigit()
            # 检查是否是 E+数字 (例如 E01)
            is_episode_prefix = prefix.startswith("E") and prefix[1:].isdigit()

            if is_digit_prefix or is_episode_prefix:
                return rest
    except ValueError:
        pass
    return filename


def process_directory_recursively(current_dir):
    """
    递归处理目录：先处理当前层级的文件夹（重命名并递归进入），
    最后处理当前层级的文件。
    """
    print(f"--- 正在扫描: {current_dir} ---")

    # 1. 获取当前目录下所有内容，并转为列表 (固定列表，防止遍历时修改导致报错)
    try:
        all_items = list(current_dir.iterdir())
    except PermissionError:
        print(f" [!] 权限拒绝，跳过: {current_dir}")
        return

    # 分类
    subdirs = [x for x in all_items if x.is_dir()]
    files = [x for x in all_items if x.is_file()]

    # --- 第一步: 处理子文件夹 (重命名 + 递归) ---
    for folder_path in subdirs:
        old_name = folder_path.name
        new_name = format_folder_name(old_name)

        if new_name and old_name != new_name:
            new_folder_path = folder_path.with_name(new_name)
            try:
                folder_path.rename(new_folder_path)
                print(f"  [文件夹] 已重命名: '{old_name}' -> '{new_name}'")
                folder_path = new_folder_path
            except OSError as e:
                print(f"  [!] 文件夹重命名失败 '{old_name}': {e}")

        process_directory_recursively(folder_path)

    # --- 第二步: 处理 .webm 文件 ---
    webm_files = sorted([f for f in files if f.suffix.lower() == ".webm"])

    if not webm_files:
        return

    counter = 1
    for file_path in webm_files:
        original_name = file_path.name

        # 1. 清理前缀
        name_without_prefix = clean_filename_prefix(original_name)

        # 2. 分离文件名和后缀
        file_stem = Path(name_without_prefix).stem
        file_suffix = file_path.suffix

        # 3. 格式化文件名主体
        cleaned_stem = format_file_name(file_stem)

        if not cleaned_stem:
            print(f"  跳过: 文件名主体为空 '{original_name}'")
            continue

        # 4. 组合新文件名
        new_filename = f"E{counter:02d}_{cleaned_stem}{file_suffix}"
        new_file_path = file_path.with_name(new_filename)

        # 5. 执行重命名
        if file_path != new_file_path:
            try:
                file_path.rename(new_file_path)
                print(f"  [文件] 已重命名: '{original_name}' -> '{new_filename}'")
            except OSError as e:
                print(f"  [!] 文件重命名失败 '{original_name}': {e}")
        else:
            print(f"  [文件] 无需更改: '{original_name}'")

        counter += 1


if __name__ == "__main__":

    # 检查工作指示文件
    if WORKING_FILE_PATH.exists():
        print("=" * 50)
        print(f"[!!!] 检测到工作指示文件 '{WORKING_FILE_PATH}' 存在。")
        print("      这意味着另一个脚本（例如视频转换）正在运行。")
        print("      为避免文件路径冲突，本脚本将立即退出，不执行重命名操作。")
        print("=" * 50)
        # 立即退出，状态码 0 表示正常退出（只是不工作）
        sys.exit(0)

    # 获取当前工作目录
    root_path = Path.cwd()

    print(f"开始处理根目录： {root_path}\n")
    process_directory_recursively(root_path)
    print("\n处理完成！")
