"""Read an EPUB once and propose conservative chapter selection without an LLM."""
import re
from ebooklib import epub
from api.services.epub_structure import table_of_contents, chapter_text

SUPPLEMENT = re.compile(r"^(?:copyright|all rights reserved|impressum|isbn|index|bibliography|bibliografie|bibliographie|"
    r"acknowledg(?:e)?ments|danksagung|about the author|über den autor|über die autorin|references|"
    r"literaturverzeichnis|table of contents|contents|inhaltsverzeichnis|endnotes|footnotes|notes|anmerkungen|"
    r"title page|half title|titelseite|titelblatt|cover|also by)\s*(?:$|:)", re.I)


def load_chapters(path):
    book = epub.read_epub(path, options={"ignore_ncx": True})
    toc = table_of_contents(book)
    chapters = []
    for order, (title, href) in enumerate(toc):
        text = chapter_text(book, href, toc)
        count = len(text.split())
        supplement = bool(SUPPLEMENT.match(title.strip()))
        title_without_number = re.sub(r"^[IVXLCDM]+[.\s]+", "", title.strip())
        heading_only = count <= 20 and " ".join(text.split()).casefold() in {
            " ".join(title.split()).casefold(), " ".join(title_without_number.split()).casefold()}
        if not supplement and count < 250:
            supplement = bool(re.search(r"all rights reserved|alle rechte vorbehalten", text[:1500], re.I))
        chapters.append({"title": title, "href": href, "order": order, "text": text,
            "word_count": count, "excerpt": text[:1400], "selected": count > 0 and not supplement and not heading_only,
            "chapter_type": "structure" if heading_only else "supplement" if supplement or not count else "content",
            "selection_reason": "Kein auslesbarer Text" if not count else
                "Gliederungsüberschrift ohne Fließtext" if heading_only else
                "Als Zusatzmaterial erkannt - bitte prüfen" if supplement else "Inhalt vorausgewählt"})
    return chapters
