import os
import re

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
keep_punct = "。？，！# :"


def chinese_to_int(s: str):
    s = s.replace("两", "二").strip()
    if s.isdigit():
        return int(s)
    if len(s) == 1 and s in _digits:
        return _digits[s]
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
    """删除除 keep_punct 外的其它标点符号"""
    return "".join(
        ch
        for ch in text
        if ch.isalnum()
        or ch.isspace()
        or ch in keep_punct
        or "\u4e00" <= ch <= "\u9fff"
    )


def replace_line(line):
    stripped = line.strip()

    # 卷
    m_volume = re.match(
        r"^第\s*([0-9零一二三四五六七八九十百两]+)\s*卷\s*[、,，]?\s*(.*)$", stripped
    )
    if m_volume:
        num = chinese_to_int(m_volume.group(1))
        title = m_volume.group(2).strip() if m_volume.group(2) else "未命名"
        return f"\n# 第{num:06d}卷 {title}\n\n"

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


def process_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    # 先删除所有 #
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

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(cleaned_lines)

    print(f"处理完成: {filename}")


if __name__ == "__main__":
    for file in os.listdir("."):
        if file.endswith(".txt"):
            process_file(file)
