# /// script
# dependencies = [
#   "ebooklib",
#   "markdown",
# ]
# ///


import os
import re
from ebooklib import epub
from markdown import markdown

def create_epub(txt_file):
    """
    Converts a single TXT file to an EPUB book.
    Supports '## 第000001章 Title' format and preserves prologue content.
    """
    book_title = os.path.splitext(txt_file)[0]
    epub_file = f"{book_title}.epub"
    
    # Initialize the EPUB book
    book = epub.EpubBook()
    book.set_title(book_title)
    book.set_language('zh')

    # Read the content
    with open(txt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex for: ## 第000001章 Title
    # Group 1: Chapter Number, Group 2: Title Name
    chapter_pattern = re.compile(r'^##\s*第(\d+)章\s*(.*)', re.MULTILINE)
    
    # Split content by the pattern
    parts = chapter_pattern.split(content)
    
    chapters = []
    
    # Handle content before the first chapter (Prologue/Introduction)
    prologue_text = parts[0].strip()
    if prologue_text:
        c = epub.EpubHtml(title='序', file_name='prologue.xhtml', lang='zh')
        # Convert markdown content to HTML
        c.content = markdown(prologue_text)
        book.add_item(c)
        chapters.append(c)

    # Iterate through split results (Groups of 3: Number, Title, Text)
    for i in range(1, len(parts), 3):
        num, title, text = parts[i], parts[i+1], parts[i+2]
        full_title = f"第{num}章 {title.strip()}"
        file_name = f"chap_{num}.xhtml"
        
        # Create chapter object
        c = epub.EpubHtml(title=full_title, file_name=file_name, lang='zh')
        # Combine title and body text converted via Markdown
        c.content = f"<h1>{full_title}</h1>" + markdown(text.strip())
        
        book.add_item(c)
        chapters.append(c)

    # Define TOC and Navigation
    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Define reading order (Spine)
    book.spine = ['nav'] + chapters
    
    # Generate the EPUB file
    epub.write_epub(epub_file, book)
    print(f"Successfully converted: {epub_file}")

def main():
    # Batch process all .txt files in the current directory
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
    
    if not txt_files:
        print("No .txt files found in the current directory.")
        return

    for f in txt_files:
        try:
            create_epub(f)
        except Exception as e:
            print(f"Error converting {f}: {e}")

if __name__ == "__main__":
    main()