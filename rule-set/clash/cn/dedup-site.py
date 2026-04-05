#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yaml
from pathlib import Path
import sys


# --- 辅助类与函数 ---


class IndentDumper(yaml.SafeDumper):
    """自定义Dumper，用于强制实现一致的YAML缩进格式。"""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def save_yaml(data: dict, file_path: Path):
    """
    将数据以特定格式安全地写入YAML文件。
    使用“写入-再重命名”的方式避免文件损坏。
    """
    temp_file_path = file_path.with_suffix(file_path.suffix + ".tmp")
    with open(temp_file_path, "w", encoding="utf-8", newline="\n") as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            indent=2,
            default_flow_style=False,
            sort_keys=False,
            width=4096,
            Dumper=IndentDumper,
            line_break="\n",
        )
    # 原子替换操作，确保安全
    temp_file_path.replace(file_path)


# --- 主处理函数 ---


def dedup_and_format_yaml(file_path: Path):
    """
    对单个YAML文件进行去重、排序和格式化，并安全地覆盖原文件。
    """
    print(f"--- 正在处理: {file_path.name} ---")
    try:
        # 1. 读取并修复文本
        raw_text = file_path.read_text(encoding="utf-8")
        repaired_text = raw_text.replace("\t", "  ")

        # 2. 加载数据
        data = yaml.safe_load(repaired_text)

        if not data or "payload" not in data or not data["payload"]:
            print(f"警告: {file_path.name} 中 'payload' 字段不存在或为空，已跳过。")
            return

        # 3. 去重与排序
        seen = set()
        str_items, other_items = [], []
        for item in data["payload"]:
            if isinstance(item, str):
                if item not in seen:
                    seen.add(item)
                    str_items.append(item)
            else:
                other_items.append(item)

        def sort_key(x):
            if x.startswith("DOMAIN,"):
                return 0, x
            if x.startswith("DOMAIN-SUFFIX,"):
                return 1, x
            return 2, x

        data["payload"] = sorted(str_items, key=sort_key) + other_items

        # 4. 调用独立的保存函数
        save_yaml(data, file_path)
        print(f"处理完成: {file_path.name}")

    except FileNotFoundError:
        print(f"错误: 文件未找到 - {file_path}", file=sys.stderr)
    except yaml.YAMLError as e:
        print(f"错误: YAML格式无法解析 - {file_path}\n{e}", file=sys.stderr)
    except Exception as e:
        print(f"错误: 处理文件时发生未知错误 - {file_path}\n{e}", file=sys.stderr)


# --- 脚本入口 ---

if __name__ == "__main__":
    # 获取当前目录下所有以 -classical.yaml 结尾的文件
    current_dir = Path(".")
    target_files = list(current_dir.glob("*-classical.yaml"))

    if not target_files:
        print("未发现匹配 *-classical.yaml 的文件。")
    else:
        print(f"共发现 {len(target_files)} 个匹配文件。")
        for file in target_files:
            dedup_and_format_yaml(file)
