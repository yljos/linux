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
    s = s.replace("两", "二").strip()
    if s.isdigit():
        return int(s)

    if "万" in s:
        parts = s.split("万")
        left = parts[0]
        right = parts[1] if len(parts) > 1 else ""

        ten_thousands = chinese_to_int(left) if left else 1
        remainder = chinese_to_int(right) if right else 0

        if ten_thousands is None or remainder is None:
            return None
        return ten_thousands * 10000 + remainder

    if len(s) == 1 and s in _digits:
        return _digits[s]

    if "千" in s:
        parts = s.split("千")
        left, right = parts[0], parts[1] if len(parts) > 1 else ""
        thousands = _digits.get(left, 1) if left else 1

        if "百" in right:
            hundred_parts = right.split("百")
            hundreds = _digits.get(hundred_parts[0], 1) if hundred_parts[0] else 1
            right2 = hundred_parts[1] if len(hundred_parts) > 1 else ""
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
        return thousands * 1000

    if "百" in s:
        parts = s.split("百")
        left, right = parts[0], parts[1] if len(parts) > 1 else ""
        hundreds = _digits.get(left, 1) if left else 1

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
        return hundreds * 100

    if "十" in s:
        parts = s.split("十")
        left, right = parts[0], parts[1] if len(parts) > 1 else ""
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

    # 正则中加入了“千”字
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
