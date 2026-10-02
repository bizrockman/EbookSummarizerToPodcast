"""EPUB reading order and non-overlapping TOC intervals, including fragments."""
import posixpath
from urllib.parse import unquote, urldefrag
from bs4 import BeautifulSoup, NavigableString, Tag


def normalize_href(href, base=""):
    path, fragment = urldefrag(href)
    path = posixpath.normpath(posixpath.join(posixpath.dirname(base), unquote(path)))
    return path + ("#" + unquote(fragment) if fragment else "")


def spine_items(book):
    items = []
    for item_id, linear in book.spine:
        item = book.get_item_with_id(item_id)
        if item and linear != "no" and "nav" not in getattr(item, "properties", []):
            items.append(item)
    return items


def table_of_contents(book):
    toc = []

    def walk(entries):
        for entry in entries:
            if isinstance(entry, (tuple, list)):
                walk([entry[0]])
                walk(entry[1])
            elif getattr(entry, "href", None):
                toc.append((getattr(entry, "title", None) or entry.href, normalize_href(entry.href)))
    walk(book.toc)
    if not toc:
        toc = [(getattr(item, "title", None) or item.get_name(), item.get_name()) for item in spine_items(book)]
    seen = set()
    return [(title, href) for title, href in toc if not (href in seen or seen.add(href))]


def chapter_text(book, href, toc):
    items = spine_items(book)
    names = [item.get_name() for item in items]
    path, fragment = urldefrag(normalize_href(href))
    if path not in names:
        raise ValueError("Kapiteldatei fehlt im EPUB-Spine: " + path)
    start_index = names.index(path)
    # Find next actual boundary in reading order. Parent/child TOC entries are
    # intervals, not overlapping complete chapters; selecting all reads once.
    hrefs = [normalize_href(value) for _, value in toc]
    current_index = hrefs.index(normalize_href(href))
    next_href = hrefs[current_index + 1] if current_index + 1 < len(hrefs) else None
    end_path, end_fragment = urldefrag(next_href) if next_href else (None, None)
    parts = []
    active = not fragment
    for index in range(start_index, len(items)):
        item = items[index]
        name = item.get_name()
        if name == end_path and not end_fragment:
            break
        soup = BeautifulSoup(item.get_content(), "html.parser")
        body = soup.body or soup
        if index == start_index and fragment and not body.find(id=fragment):
            raise ValueError("Kapitelanker fehlt: " + href)
        if name == end_path and end_fragment and not body.find(id=end_fragment):
            raise ValueError("Kapitel-Endanker fehlt: " + next_href)
        for node in body.descendants:
            if isinstance(node, Tag):
                if name == end_path and end_fragment and node.get("id") == end_fragment:
                    return "".join(parts).strip()
                if index == start_index and fragment and node.get("id") == fragment:
                    active = True
                if active and node.name in ("p", "h1", "h2", "h3", "h4", "li", "blockquote", "div", "br"):
                    parts.append("\n\n")
            elif isinstance(node, NavigableString) and active:
                if any(parent.name in ("script", "style", "nav") for parent in node.parents):
                    continue
                value = str(node).strip()
                if value:
                    parts.append(value + " ")
    return "".join(parts).strip()
