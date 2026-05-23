import os
import sys
import yaml
import shutil

TEMPLATE_FILE = "cn-site-classical.yaml"  # 默认模板文件名，可修改


def load_yaml(p_filepath):
    with open(p_filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_missing(a, b, current_path=None):
    """
    返回a中不被b包含的所有路径和内容
    """
    if current_path is None:
        current_path = []
    missing_items = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k, v in a.items():
            if k not in b:
                missing_items.append((".".join(current_path + [str(k)]), v))
            else:
                missing_items.extend(find_missing(v, b[k], current_path + [str(k)]))
    elif isinstance(a, list) and isinstance(b, list):
        for idx, item_a in enumerate(a):
            if not any(is_subset(item_a, item_b) for item_b in b):
                missing_items.append((".".join(current_path + [f"[{idx}]"]), item_a))
    else:
        if a != b:
            missing_items.append((".".join(current_path), a))
    return missing_items


def is_subset(a, b):
    return not find_missing(a, b)


def merge_into_template(target_data, source_data):
    """
    把 source_data 中缺失的项合并进 target_data（就地修改），不会覆盖已存在的值。
    返回 True 如果 target_data 被修改过。
    """
    changed = False
    if source_data is None:
        return False

    if isinstance(source_data, dict):
        if target_data is None or not isinstance(target_data, dict):
            return False
        for k, v in source_data.items():
            if k not in target_data:
                target_data[k] = v
                changed = True
            else:
                if isinstance(v, dict) and isinstance(target_data[k], dict):
                    if merge_into_template(target_data[k], v):
                        changed = True
                elif isinstance(v, list) and isinstance(target_data[k], list):
                    for item in v:
                        if not any(
                            is_subset(item, existing) for existing in target_data[k]
                        ):
                            target_data[k].append(item)
                            changed = True
    elif isinstance(source_data, list):
        if target_data is None or not isinstance(target_data, list):
            return False
        for item in source_data:
            if not any(is_subset(item, existing) for existing in target_data):
                target_data.append(item)
                changed = True
    else:
        return False
    return changed


if __name__ == "__main__":
    template_file = sys.argv[1] if len(sys.argv) > 1 else TEMPLATE_FILE
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, template_file)

    if not os.path.exists(template_path):
        print(f"模板文件 {template_file} 不存在，创建空模板...")
        with open(template_path, "w", encoding="utf-8") as tf:
            yaml.safe_dump({}, tf, allow_unicode=True, sort_keys=False)

    template = load_yaml(template_path)
    if template is None:
        template = {}
    for filename in os.listdir(current_dir):
        if filename.endswith(".yaml") and filename not in (
            template_file,
            "cn-site.yaml",
            "cn-ip.yaml",
        ):
            file_path = os.path.join(current_dir, filename)
            try:
                data = load_yaml(file_path)
                if data is None:
                    print(f"{filename}: 内容为空，跳过")
                    continue

                missing = find_missing(data, template)
                if not missing:
                    print(f"{filename}: 全部包含在 {template_file} 中")
                else:
                    print(f"{filename}: 未全部包含在 {template_file} 中，缺失条目:")
                    for path, value in missing:
                        print(f"  - {path}: {value}")

                    merged = merge_into_template(template, data)
                    if merged:
                        print(
                            f"  -> 已把 {filename} 中缺失的条目合并到 {template_file}"
                        )
            except Exception as e:
                print(f"{filename}: 解析失败 - {e}")

    try:
        backup_path = template_path + ".bak"
        shutil.copy2(template_path, backup_path)
        with open(template_path, "w", encoding="utf-8") as tf:
            yaml.safe_dump(template, tf, allow_unicode=True, sort_keys=False)
        print(f"已备份原模板为: {backup_path}")
        print(f"已更新模板: {template_path}")
    except Exception as e:
        print(f"写回模板失败: {e}")
