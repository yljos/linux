import re
from pathlib import Path

_digits = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "两": 2,
}

keep_punct = "。？，！ : .……"


def chinese_to_int(s: str):
    # Recursively convert Chinese numerals to integers
    s = s.replace("两", "二").strip()
    if not s: return None
    if s.isdigit(): return int(s)

    if all(c in _digits for c in s):
        total = 0
        for ch in s: total = total * 10 + _digits[ch]
        return total

    for unit, multiplier in [("万", 10000), ("千", 1000), ("百", 100), ("十", 10)]:
        if unit in s:
            parts = s.split(unit, 1)
            left = chinese_to_int(parts[0]) if parts[0] else 1
            right = chinese_to_int(parts[1]) if parts[1] else 0
            if left is None or right is None: return None
            return left * multiplier + right
    return None


def clean_punct(text):
    # Keep alphanumeric, space, specific punctuation, and CJK characters
    return "".join(
        ch for ch in text
        if ch.isalnum() or ch.isspace() or ch in keep_punct or "\u4e00" <= ch <= "\u9fff"
    )


def replace_line(line):
    # Process a single line safely
    cleaned = clean_punct(line).strip()
    if not cleaned:
        return ""

    # Match Volume (卷)
    m_volume = re.match(r"^第\s*([0-9零一二三四五六七八九十百千万两]+)\s*卷\s*[、,，]?\s*(.*)$", cleaned)
    if m_volume:
        num = chinese_to_int(m_volume.group(1))
        title = m_volume.group(2).strip() if m_volume.group(2) else "未命名"
        return f"\n# 第{num:03d}卷 {title}\n\n"

    # Match Chapter (章/节)
    m_chapter = re.match(r"^第\s*([0-9零一二三四五六七八九十百千万两]+)\s*[节章]\s*[、,，]?\s*(.*)$", cleaned)
    if m_chapter:
        num = chinese_to_int(m_chapter.group(1))
        title = m_chapter.group(2).strip() if m_chapter.group(2) else "未命名"
        return f"\n## 第{num:06d}章 {title}\n\n"

    # Match Numeric Chapter (1. xxx)
    m_numdot = re.match(r"^([0-9零一二三四五六七八九十百千万两]+)\.\s*(.*)$", cleaned)
    if m_numdot:
        num = chinese_to_int(m_numdot.group(1))
        title = m_numdot.group(2).strip() if m_numdot.group(2) else "未命名"
        return f"\n## 第{num:06d}章 {title}\n\n"

    return cleaned + "\n"


def process_file(file_path: Path):
    # Detect encoding using a small chunk
    try:
        with open(file_path, "rt", encoding="utf-8") as f:
            f.read(4096)
        encoding = "utf-8"
    except UnicodeDecodeError:
        encoding = "gb18030"

    temp_file = file_path.with_suffix(".tmp")

    try:
        # Stream processing to keep memory usage minimal (O(1) memory)
        with open(file_path, "rt", encoding=encoding) as f_in, \
                open(temp_file, "wt", encoding="utf-8") as f_out:

            empty_count = 0
            for line in f_in:
                processed = replace_line(line)
                if processed == "\n" or processed == "":
                    empty_count += 1
                    if empty_count <= 2:  # Limit consecutive empty lines
                        f_out.write("\n")
                else:
                    empty_count = 0
                    f_out.write(processed)

        temp_file.replace(file_path)
        print(f"Processed: {file_path.name}")
    except Exception as e:
        print(f"Error: {e}")
        if temp_file.exists(): temp_file.unlink()


if __name__ == "__main__":
    for txt_file in Path.cwd().glob("*.txt"):
        process_file(txt_file)
