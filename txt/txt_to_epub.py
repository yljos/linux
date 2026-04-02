import os
import re
from ebooklib import epub
from markdown import markdown
from PIL import Image, ImageDraw, ImageFont

def generate_cover_jpg(title, author, filepath):
    """Generate a simple JPG cover."""
    img = Image.new('RGB', (600, 800), color='#332F2F')
    draw = ImageDraw.Draw(img)
    
    # Common Chinese fonts for Windows/Linux
    font_paths = [
        "msyh.ttc",            
        "simhei.ttf",          
        "wqy-microhei.ttc",    
        "NotoSansCJK-Regular.ttc" 
    ]
    
    font_title, font_author = None, None
    for path in font_paths:
        try:
            # Use size 40 for title, 30 for author
            font_title = ImageFont.truetype(path, 40)
            font_author = ImageFont.truetype(path, 30)
            break
        except IOError:
            continue
            
    if not font_title:
        # Fallback if no Chinese fonts found
        font_title = ImageFont.load_default()
        font_author = ImageFont.load_default()

    draw.text((300, 320), title, font=font_title, fill='#F58B0A', anchor="mm")
    draw.text((300, 400), author, font=font_author, fill='#E3DC10', anchor="mm")
    
    img.save(filepath, "JPEG")

def create_epub(txt_file):
    book_title = os.path.splitext(txt_file)[0]
    epub_file = f"{book_title}.epub"
    
    book = epub.EpubBook()
    book.set_title(book_title)
    book.add_author("18")
    book.set_language('zh')

    # Generate temp JPG, embed it, then remove temp file
    cover_path = f"tmp_cover_{book_title}.jpg"
    generate_cover_jpg(book_title, "18", cover_path)
    with open(cover_path, 'rb') as img:
        book.set_cover("cover.jpg", img.read())
    os.remove(cover_path)

    with open(txt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    chapter_pattern = re.compile(r'^##\s*第(\d+)章\s*(.*)', re.MULTILINE)
    parts = chapter_pattern.split(content)
    
    chapters = []
    
    prologue_text = parts[0].strip()
    if prologue_text:
        c = epub.EpubHtml(title='序', file_name='prologue.xhtml', lang='zh')
        c.content = markdown(prologue_text)
        book.add_item(c)
        chapters.append(c)

    for i in range(1, len(parts), 3):
        num, title, text = parts[i], parts[i+1], parts[i+2]
        full_title = f"第{num}章 {title.strip()}"
        
        file_name = f"chap_{num}.xhtml"
        
        c = epub.EpubHtml(title=full_title, file_name=file_name, lang='zh')
        c.content = f"<h1>{full_title}</h1>" + markdown(text.strip())
        
        book.add_item(c)
        chapters.append(c)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    book.spine = ['nav'] + chapters
    
    epub.write_epub(epub_file, book)
    print(f"Successfully converted: {epub_file}")

def main():
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
    if not txt_files:
        return
    for f in txt_files:
        try:
            create_epub(f)
        except Exception as e:
            print(f"Error converting {f}: {e}")

if __name__ == "__main__":
    main()