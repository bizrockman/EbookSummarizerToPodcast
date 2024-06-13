import ebooklib
from ebooklib import epub

from bs4 import BeautifulSoup


def load_epub(file_path):
    print(f"Lade EPUB-Datei: {file_path}")
    book = epub.read_epub(file_path)
    print("EPUB-Datei erfolgreich geladen.")
    return book


def extract_toc_from_ncx(book):
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_NAVIGATION:
            soup = BeautifulSoup(item.get_content(), 'xml')
            nav_points = soup.find_all('navPoint')
            toc = [(nav_point.navLabel.text, nav_point.content['src']) for nav_point in nav_points]
            return toc
    return []


def extract_toc_from_nav(book):
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_NAVIGATION:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            toc = [(a.text, a['href']) for a in soup.select('nav[epub|type="toc"] ol li a')]
            return toc
    return []


def extract_chapter_content(book, href):
    # Extract the content of the chapter given its href
    content = ""
    for item in book.get_items():
        if item.get_name() == href.split('#')[0]:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            content = soup.get_text(separator='\n')
            break
    return content


def extract_toc(book):
    toc = extract_toc_from_ncx(book)
    if not toc:
        toc = extract_toc_from_nav(book)
    return toc


def display_toc(toc):
    for idx, (title, href) in enumerate(toc):
        print(f"{idx + 1}. {title}: {href}")