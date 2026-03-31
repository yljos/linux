import re
from pathlib import Path

_digits = {
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "两": 2,
}

# 保留标点集合
keep_punct = "。？，！# : .……"


def chinese_to_int(s: str):
    """
    (保持原逻辑不变)
    将中文数字转换为整数
    """
    s = s.replace("两", "二").strip()
    if s.isdigit():
        return int(s)
    if len(s) == 1 and s in _digits:
        return _digits[s]
    # 支持千
    if "千" in s:
        parts = s.split("千")
        left = parts[0]
        right = parts[1] if len(parts) > 1 else ""
        thousands = _digits.get(left, 1) if left else 1
        # 千后面可能有百
        if "百" in right:
            hundred_parts = right.split("百")
            hundreds = _digits.get(hundred_parts[0], 1) if hundred_parts[0] else 1
            right2 = hundred_parts[1] if len(hundred_parts) > 1 else ""
            # 百后面可能有十
            if "十" in right2:
                ten_parts = right2.split("十")
                tens = _digits.get(ten_parts[0], 1) if ten_parts[0] else 1
                ones = (
                    _digits.get(ten_parts[1], 0)
                    if len(ten_parts) > 1 and ten_parts[1]
                    else 0
                )
                return thousands * 1000 + hundreds * 100 + tens * 10 + ones
            elif right2:
                ones = _digits.get(right2, 0)
                return thousands * 1000 + hundreds * 100 + ones
            else:
                return thousands * 1000 + hundreds * 100
        elif "十" in right:
            ten_parts = right.split("十")
            tens = _digits.get(ten_parts[0], 1) if ten_parts[0] else 1
            ones = (
                _digits.get(ten_parts[1], 0)
                if len(ten_parts) > 1 and ten_parts[1]
                else 0
            )
            return thousands * 1000 + tens * 10 + ones
        elif right:
            ones = _digits.get(right, 0)
            return thousands * 1000 + ones
        else:
            return thousands * 1000
    # 支持百
    if "百" in s:
        parts = s.split("百")
        left = parts[0]
        right = parts[1] if len(parts) > 1 else ""
        hundreds = _digits.get(left, 1) if left else 1
        # 处理百后面可能有十
        if "十" in right:
            ten_parts = right.split("十")
            tens = _digits.get(ten_parts[0], 1) if ten_parts[0] else 1
            ones = (
                _digits.get(ten_parts[1], 0)
                if len(ten_parts) > 1 and ten_parts[1]
                else 0
            )
            return hundreds * 100 + tens * 10 + ones
        elif right:
            ones = _digits.get(right, 0)
            return hundreds * 100 + ones
        else:
            return hundreds * 100
    # 支持十
    if "十" in s:
        parts = s.split("十")
        left = parts[0]
        right = parts[1] if len(parts) > 1 else ""
        tens = 1 if left == "" else _digits.get(left, 0)
        ones = _digits.get(right, 0) if right else 0
        return tens * 10 + ones
    total = 0
    for ch in s:
        if ch not in _digits:
            return None
        total = total * 10 + _digits[ch]
    return total


def clean_punct(text):
    """
    (保持原逻辑不变)
    删除除 keep_punct 外的其它标点符号
    """
    return "".join(
        ch
        for ch in text
        if ch.isalnum()
        or ch.isspace()
        or ch in keep_punct
        or "\u4e00" <= ch <= "\u9fff"
    )


def replace_line(line):
    """(保持原逻辑不变)"""
    stripped = line.strip()

    # 卷
    m_volume = re.match(
        r"^第\s*([0-9零一二三四五六七八九十百两]+)\s*卷\s*[、,，]?\s*(.*)$", stripped
    )
    if m_volume:
        num = chinese_to_int(m_volume.group(1))
        title = m_volume.group(2).strip() if m_volume.group(2) else "未命名"
        return f"\n# 第{num:03d}卷 {title}\n\n"

    # 章/节
    m_chapter = re.match(
        r"^第\s*([0-9零一二三四五六七八九十百两]+)\s*[节章]\s*[、,，]?\s*(.*)$",
        stripped,
    )
    if m_chapter:
        num = chinese_to_int(m_chapter.group(1))
        title = m_chapter.group(2).strip() if m_chapter.group(2) else "未命名"
        return f"\n## 第{num:06d}章 {title}\n\n"

    # 数字标题
    m_numdot = re.match(r"^([0-9零一二三四五六七八九十百两]+)\.\s*(.*)$", stripped)
    if m_numdot:
        num = chinese_to_int(m_numdot.group(1))
        title = m_numdot.group(2).strip() if m_numdot.group(2) else "未命名"
        return f"\n## 第{num:06d}章 {title}\n\n"

    # 已经是标题
    if stripped.startswith("# ") or stripped.startswith("## "):
        return f"\n{stripped}\n\n"

    # 普通行：清理标点、顶格输出，不保留空行
    return clean_punct(stripped) + "\n"


def process_file(file_path: Path):
    """
    使用 pathlib 读取、处理并写入文件
    """
    # pathlib 读取文件内容
    # errors="ignore" 或 "replace" 可以防止编码错误，这里使用 strict (默认)
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"编码错误跳过: {file_path.name}")
        return

    # 先删除所有 # (保持原逻辑)
    content = content.replace("#", "")

    lines = content.splitlines()

    new_lines = [replace_line(line) for line in lines]

    # 删除多余空行，只保留标题前后空行
    cleaned_lines = []
    for i, line in enumerate(new_lines):
        if line.strip() == "":
            # 空行前后都是标题则保留
            prev_line = new_lines[i - 1] if i > 0 else ""
            next_line = new_lines[i + 1] if i + 1 < len(new_lines) else ""
            if (prev_line.startswith("#") or prev_line.startswith("##")) or (
                next_line.startswith("#") or next_line.startswith("##")
            ):
                cleaned_lines.append("\n")
            # 否则跳过空行
        else:
            cleaned_lines.append(line)

    # pathlib 写入文件
    # write_text 需要传入字符串，所以用 join 将列表合并
    file_path.write_text("".join(cleaned_lines), encoding="utf-8")

    print(f"处理完成: {file_path.name}")


if __name__ == "__main__":
    # 使用 pathlib 的 glob 查找当前目录下所有 .txt 文件
    # Path.cwd() 获取当前工作目录
    for txt_file in Path.cwd().glob("*.txt"):
        process_file(txt_file)
