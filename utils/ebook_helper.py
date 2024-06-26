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


#def extract_chapter_content(book, href):
#    # Extract the content of the chapter given its href
#    content = ""
#    for item in book.get_items():
#        if item.get_name() == href.split('#')[0]:
#            soup = BeautifulSoup(item.get_content(), 'html.parser')
#            content = soup.get_text(separator='\n')
#            break
#    return content


def get_spine_order(book):
    spine = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        spine.append(item.get_name())
    return spine


def extract_chapter_content(book, href, toc):
    spine_order = get_spine_order(book)
    content = ""
    start_index = spine_order.index(href.split('#')[0])
    print(f"Chapter href: {href}")
    print(f"Start index: {start_index}")
    # Iterate through the spine from the start index to concatenate content
    for item_href in spine_order[start_index:]:
        print(f"Item href: {item_href}")
        item = book.get_item_with_href(item_href)
        if item:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            content += soup.get_text(separator='\n')
        # Stop if the next spine item is a new chapter (based on navPoint from toc.ncx)
        next_index = spine_order.index(item_href) + 1
        if next_index < len(spine_order):
            next_item = spine_order[next_index]
            if any(chapter_href.split('#')[0] == next_item for _, chapter_href in toc):
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