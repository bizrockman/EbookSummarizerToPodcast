import unittest
from ebooklib import epub
from api.services.epub_structure import chapter_text, table_of_contents


class EpubStructureTests(unittest.TestCase):
    def setUp(self):
        self.book = epub.EpubBook()
        self.one = epub.EpubHtml(uid="one", file_name="one.xhtml", title="One")
        self.one.content = '<h1 id="a">First</h1><p>Unique <em>first</em> evidence.</p><h2 id="b">Second</h2><p>Unique second evidence.</p>'
        self.two = epub.EpubHtml(uid="two", file_name="two.xhtml", title="Two")
        self.two.content = '<h1>Third</h1><p>Unique third evidence.</p>'
        self.book.add_item(self.two)  # Manifest intentionally differs from reading order.
        self.book.add_item(self.one)
        self.book.spine = [("one", "yes"), ("two", "yes")]
        self.book.toc = [epub.Link("one.xhtml#a", "First", "a"), epub.Link("one.xhtml#b", "Second", "b"),
                         epub.Link("two.xhtml", "Third", "c")]

    def test_fragments_are_disjoint_and_follow_spine(self):
        toc = table_of_contents(self.book)
        texts = [chapter_text(self.book, href, toc) for _, href in toc]
        self.assertIn("Unique first evidence.", texts[0])
        self.assertNotIn("second", texts[0])
        self.assertIn("Unique second evidence.", texts[1])
        self.assertNotIn("third", texts[1])
        self.assertIn("Unique third evidence.", texts[2])

    def test_missing_fragment_fails_instead_of_duplicating_chapter(self):
        toc = [("Missing", "one.xhtml#missing")]
        with self.assertRaises(ValueError):
            chapter_text(self.book, toc[0][1], toc)

    def test_missing_toc_uses_spine(self):
        self.book.toc = []
        self.assertEqual([href for _, href in table_of_contents(self.book)], ["one.xhtml", "two.xhtml"])


if __name__ == "__main__":
    unittest.main()
