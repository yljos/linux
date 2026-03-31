import os
import subprocess
import yaml
import json
from collections import defaultdict

# --- 配置 ---

# 自动适配可执行文件名
mihomo_bin = "mihomo-windows-amd64.exe" if os.name == "nt" else "./mihomo-linux-amd64"
singbox_bin = "sing-box.exe" if os.name == "nt" else "./sing-box"


# --- 辅助类与函数 ---


class IndentDumper(yaml.SafeDumper):
    """自定义Dumper，用于强制实现一致的YAML缩进格式。"""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def ensure_dir(path):
    """确保目录存在，如果不存在则创建。"""
    if not os.path.exists(path):
        os.makedirs(path)


def yaml_to_json_rule(input_path, output_path):
    """将Clash规则的yaml文件转换为sing-box规则的json文件。"""
    with open(input_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rule = defaultdict(list)
    for item in data.get("payload", []):
        if isinstance(item, str):
            if "," not in item:
                rule["ip_cidr"].append(item)
            elif item.startswith("DOMAIN,"):
                rule["domain"].append(item.split(",", 1)[1])
            elif item.startswith("DOMAIN-SUFFIX,"):
                rule["domain_suffix"].append(item.split(",", 1)[1])
            elif item.startswith("DOMAIN-KEYWORD,"):
                rule["domain_keyword"].append(item.split(",", 1)[1])
            elif item.startswith("DOMAIN-REGEX,"):
                rule["domain_regex"].append(item.split(",", 1)[1])
            # 可根据需要扩展更多类型

    json_obj = {"version": 3, "rules": [dict(rule)]}
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(json_obj, f, ensure_ascii=False, indent=2)


def enforce_yaml_lf(file_path):
    """读取yaml文件，格式化后以LF换行符覆盖写回。"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    with open(file_path, "w", encoding="utf-8", newline="\n") as f:
        # 使用在全局作用域中定义的 IndentDumper
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


# --- 脚本主逻辑 ---

print("--- 开始处理 clash 目录 ---")
# 合并循环：一次遍历 clash 目录，执行所有相关操作
for root, dirs, files in os.walk("clash"):
    for file in files:
        yaml_path = os.path.join(root, file)
        lname = file.lower()

        # 1. 格式化所有相关的 yaml 文件
        if lname.endswith(("-ip.yaml", "-site.yaml", "-site-classical.yaml")):
            print(f"[格式化] {yaml_path}")
            enforce_yaml_lf(yaml_path)

        # 2. clash -> sing-box (json)
        if lname.endswith(("-ip.yaml", "-site-classical.yaml")):
            rel_dir = os.path.relpath(root, "clash")
            singbox_target_dir = os.path.join("sing-box", rel_dir)
            ensure_dir(singbox_target_dir)

            if lname.endswith("-site-classical.yaml"):
                prefix = file[: -len("-site-classical.yaml")]
                json_name = prefix + "-site.json"
            else:
                json_name = os.path.splitext(file)[0] + ".json"
            json_path = os.path.join(singbox_target_dir, json_name)

            print(f"[转 JSON] {yaml_path} -> {json_path}")
            yaml_to_json_rule(yaml_path, json_path)

        # 3. clash -> mihomo (mrs)
        if lname.endswith("-ip.yaml") or (
            lname.endswith("-site.yaml") and not lname.endswith("-site-classical.yaml")
        ):
            mrs_path = os.path.splitext(yaml_path)[0] + ".mrs"
            mode = "ipcidr" if lname.endswith("-ip.yaml") else "domain"
            print(f"[转 MRS] {yaml_path} -> {mrs_path} (mode={mode})")
            subprocess.run(
                [mihomo_bin, "convert-ruleset", mode, "yaml", yaml_path, mrs_path]
            )

print("\n--- 开始处理 sing-box 目录 ---")
# 单独循环：处理 sing-box 目录下的 json 文件，编译为 srs
for root, dirs, files in os.walk("sing-box"):
    for file in files:
        if file.endswith(".json"):
            json_path = os.path.join(root, file)
            print(f"[编译 SRS] {json_path}")
            subprocess.run([singbox_bin, "rule-set", "compile", json_path])

print("\n全部转换完成")
