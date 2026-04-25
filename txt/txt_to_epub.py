import os
import re
from ebooklib import epub
from markdown import markdown
from PIL import Image, ImageDraw, ImageFont

def generate_cover_jpg(title, author, filepath):
    """Generate a simple JPG cover."""
    img = Image.new("RGB", (600, 800), color="#332F2F")
    draw = ImageDraw.Draw(img)

    # Common Chinese fonts for Windows/Linux
    font_paths = [
        "msyh.ttc",
        "simhei.ttf",
        "wqy-microhei.ttc",
        "NotoSansCJK-Regular.ttc",
    ]

    font_title, font_author = None, None
    for path in font_paths:
        try:
            font_title = ImageFont.truetype(path, 40)
            font_author = ImageFont.truetype(path, 30)
            break
        except IOError:
            continue

    if not font_title:
        font_title = ImageFont.load_default()
        font_author = ImageFont.load_default()

    draw.text((300, 320), title, font=font_title, fill="#F58B0A", anchor="mm")
    draw.text((300, 400), author, font=font_author, fill="#E3DC10", anchor="mm")

    img.save(filepath, "JPEG")

def create_epub(txt_file):
    book_title = os.path.splitext(txt_file)[0]
    epub_file = f"{book_title}.epub"

    book = epub.EpubBook()
    book.set_title(book_title)
    book.add_author("18")
    book.set_language("zh")

    # 生成并嵌入封面
    cover_path = f"tmp_cover_{book_title}.jpg"
    generate_cover_jpg(book_title, "18", cover_path)
    with open(cover_path, "rb") as img:
        book.set_cover("cover.jpg", img.read())
    os.remove(cover_path)

    chapters = []
    current_title = "序"
    current_file_name = "prologue.xhtml"
    current_lines = []
    
    # 内部文件自增计数器，解决 txt 中章节号标错/重复导致的 Duplicate name 报错
    chapter_counter = 0 
    
    # 恢复你文件中的正则：匹配 "## 第xxx章"
    chapter_pattern = re.compile(r"^##\s*第(\d+)章\s*(.*)")

    def add_chapter(title, file_name, lines):
        """辅助函数：将收集到的文本写入 EPUB 章节"""
        if not lines:
            return
        content = "".join(lines).strip()
        if not content:
            return
        
        c = epub.EpubHtml(title=title, file_name=file_name, lang="zh")
        if file_name == "prologue.xhtml":
            c.content = markdown(content)
        else:
            c.content = f"<h1>{title}</h1>\n" + markdown(content)
            
        book.add_item(c)
        chapters.append(c)

    # 逐行读取，防止大体积 txt 撑爆内存
    with open(txt_file, "rt", encoding="utf-8") as f:
        for line in f:
            match = chapter_pattern.match(line)
            if match:
                # 遇到新章节，先结算并保存上一章的内容
                add_chapter(current_title, current_file_name, current_lines)
                
                # 章节计数器加 1，生成唯一的文件名
                chapter_counter += 1
                
                num = match.group(1)
                title_text = match.group(2).strip()
                
                # 外部显示的 title 使用提取的文本，内部 file_name 使用自增数字
                current_title = f"第{num}章 {title_text}"
                current_file_name = f"chap_{chapter_counter:06d}.xhtml" 
                current_lines = []
            else:
                # 普通文本行，加入当前章节缓存
                current_lines.append(line)

    # 循环结束后，保存最后一章
    add_chapter(current_title, current_file_name, current_lines)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    epub.write_epub(epub_file, book)
    print(f"Successfully converted: {epub_file}")

def main():
    txt_files = [f for f in os.listdir(".") if f.endswith(".txt")]
    if not txt_files:
        return
    for f in txt_files:
        try:
            create_epub(f)
        except Exception as e:
            print(f"Error converting {f}: {e}")

if __name__ == "__main__":
    main()