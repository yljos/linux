from pathlib import Path
import yaml
import sys

# --- 配置区 ---
# 请在这里修改您要扫描的根目录
INPUT_DIRECTORY = Path("./clash")  # 要扫描的输入目录


# --- 配置区结束 ---


def process_file(inp: Path, outp: Path):
    """
    处理单个 classical YAML 文件并生成新版本。
    :param inp: 输入文件路径 (Path 对象)
    :param outp: 输出文件路径 (Path 对象)
    """
    print(f"--- 正在处理: {inp} ---")
    data = yaml.safe_load(inp.read_text(encoding="utf-8")) or {}

    payload = data.get("payload")
    if payload is None:
        print(f"警告: 在 {inp.name} 中未找到 'payload'，跳过此文件。")
        return

    for item in payload:
        if isinstance(item, str):
            if (
                item.startswith("DOMAIN-KEYWORD,")
                or item.startswith("DOMAIN-REGEX,")
                or item.startswith("PROCESS-NAME,")
            ):
                print(
                    f'错误: 在 {inp.name} 中发现不支持的规则类型: {item.split(",", 1)[0]}',
                    file=sys.stderr,
                )
                return

    new_payload = []
    for item in payload:
        if isinstance(item, str):
            if item.startswith("DOMAIN-SUFFIX,"):
                rest = item.split(",", 1)[1].strip()
                if rest:
                    new_payload.append("+.{}".format(rest.lstrip(".")))
                    continue
            if item.startswith("DOMAIN,"):
                rest = item.split(",", 1)[1].strip()
                if rest:
                    new_payload.append(rest)
                    continue
        new_payload.append(item)

    data["payload"] = new_payload
    outp.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    print(f"已生成: {outp}")


def main():
    input_dir = INPUT_DIRECTORY

    if not input_dir.is_dir():
        print(f"错误: 输入目录 '{input_dir}' 不存在或不是一个目录。")
        return

    print(f"开始从目录 {input_dir} 递归扫描...")
    print(f"输出文件将保存在源文件旁边。")

    found_files = list(input_dir.rglob("*-classical.yaml"))

    if not found_files:
        print("未找到任何 *-classical.yaml 文件。")
        return

    for inp_path in found_files:
        # 构建输出文件名
        outp_name = inp_path.name.replace("-classical.yaml", ".yaml")
        # 直接使用 with_name 在源文件相同目录下创建输出文件
        outp_path = inp_path.with_name(outp_name)

        process_file(inp_path, outp_path)

    print("\n--- 所有文件处理完毕 ---")


if __name__ == "__main__":
    main()
