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

keep_punct = "。？，！ : .……"


def chinese_to_int(s: str):
    """Recursively convert Chinese numerals to integers."""
    s = s.replace("两", "二").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)

    # Handle pure numeric translations (e.g., "一二三" -> 123, "零三" -> 3)
    if all(c in _digits for c in s):
        total = 0
        for ch in s:
            total = total * 10 + _digits[ch]
        return total

    # Recursively parse units from largest to smallest
    for unit, multiplier in [("万", 10000), ("千", 1000), ("百", 100), ("十", 10)]:
        if unit in s:
            parts = s.split(unit, 1)
            left_str, right_str = parts[0], parts[1]

            left = chinese_to_int(left_str) if left_str else 1
            right = chinese_to_int(right_str) if right_str else 0

            if left is None or right is None:
                return None
            return left * multiplier + right

    return None


def clean_punct(text):
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
    if not stripped:
        return ""

    m_volume = re.match(
        r"^第\s*([0-9零一二三四五六七八九十百千万两]+)\s*卷\s*[、,，]?\s*(.*)$",
        stripped,
    )
    if m_volume:
        num = chinese_to_int(m_volume.group(1))
        title = m_volume.group(2).strip() if m_volume.group(2) else "未命名"
        return f"\n# 第{num:03d}卷 {title}\n\n"

    m_chapter = re.match(
        r"^第\s*([0-9零一二三四五六七八九十百千万两]+)\s*[节章]\s*[、,，]?\s*(.*)$",
        stripped,
    )
    if m_chapter:
        num = chinese_to_int(m_chapter.group(1))
        title = m_chapter.group(2).strip() if m_chapter.group(2) else "未命名"
        return f"\n## 第{num:06d}章 {title}\n\n"

    m_numdot = re.match(r"^([0-9零一二三四五六七八九十百千万两]+)\.\s*(.*)$", stripped)
    if m_numdot:
        num = chinese_to_int(m_numdot.group(1))
        title = m_numdot.group(2).strip() if m_numdot.group(2) else "未命名"
        return f"\n## 第{num:06d}章 {title}\n\n"

    return clean_punct(stripped) + "\n"


def get_utf8_content(file_path: Path) -> str:
    raw_bytes = file_path.read_bytes()
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("gb18030")


def process_file(file_path: Path):
    try:
        content = get_utf8_content(file_path)
    except UnicodeDecodeError:
        print(f"Skipped (Unsupported encoding): {file_path.name}")
        return

    content = content.replace("#", "")

    lines = content.splitlines()
    new_lines = [replace_line(line) for line in lines]
    cleaned_content = "".join(new_lines)

    cleaned_content = re.sub(r"\n{3,}", "\n\n", cleaned_content)

    file_path.write_text(cleaned_content, encoding="utf-8")
    print(f"Processed: {file_path.name}")


if __name__ == "__main__":
    for txt_file in Path.cwd().glob("*.txt"):
        process_file(txt_file)
