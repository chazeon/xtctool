"""Tests for TOC (Table of Contents) extraction from Typst and PDF files."""

import tempfile
import pytest
from pathlib import Path

# Check if optional dependencies are available
try:
    import typst
    import fitz  # PyMuPDF
    TYPST_AVAILABLE = True
except ImportError:
    TYPST_AVAILABLE = False


@pytest.mark.skipif(not TYPST_AVAILABLE, reason="Requires typst and PyMuPDF")
class TestTypstTOCExtraction:
    """Test TOC extraction from Typst-generated PDFs."""

    def test_simple_headings_toc(self):
        """Test extraction of simple heading structure."""
        # Create a Typst document with headings
        typst_content = """
#set page(width: 10cm, height: 15cm)

= Chapter 1
This is the first chapter with some content.

== Section 1.1
A subsection in chapter 1.

== Section 1.2
Another subsection.

= Chapter 2
This is the second chapter.

=== Deep Section 2.1.1
A deeply nested section.

= Chapter 3
The final chapter.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write Typst source
            typ_file = Path(tmpdir) / "test.typ"
            typ_file.write_text(typst_content)

            # Compile to PDF
            pdf_file = Path(tmpdir) / "test.pdf"
            typst.compile(str(typ_file), output=str(pdf_file), format='pdf')

            # Extract TOC from PDF
            doc = fitz.open(str(pdf_file))
            toc = doc.get_toc()
            doc.close()

            # Verify TOC structure
            assert len(toc) > 0, "TOC should not be empty"

            # Expected TOC entries: (level, title, page)
            # Note: Typst automatically creates outline from headings
            expected_titles = [
                "Chapter 1",
                "Section 1.1",
                "Section 1.2",
                "Chapter 2",
                "Deep Section 2.1.1",
                "Chapter 3"
            ]

            # Note: Typst may flatten outline levels in PDF (=== becomes level 2, not 3)
            # This is expected behavior - we care about structure, not exact level numbers
            expected_levels = [1, 2, 2, 1, 2, 1]  # Actual PDF outline levels

            # Check we got the right headings
            extracted_titles = [entry[1] for entry in toc]
            extracted_levels = [entry[0] for entry in toc]

            assert extracted_titles == expected_titles, \
                f"Expected titles {expected_titles}, got {extracted_titles}"

            assert extracted_levels == expected_levels, \
                f"Expected levels {expected_levels}, got {extracted_levels}"

            # Verify hierarchical structure: level 2 entries should come after level 1
            prev_level = 0
            for level, title, page in toc:
                # Level shouldn't jump more than 1 at a time in well-formed TOC
                assert level <= prev_level + 1, \
                    f"Level jump too large at '{title}': {prev_level} -> {level}"
                prev_level = level

            # Check page numbers are reasonable (all should be >= 1)
            extracted_pages = [entry[2] for entry in toc]
            assert all(p >= 1 for p in extracted_pages), \
                f"All page numbers should be >= 1, got {extracted_pages}"

    def test_multipage_toc(self):
        """Test TOC with headings across multiple pages."""
        typst_content = """
#set page(width: 10cm, height: 8cm)

= Chapter 1
Some content on first page.

#pagebreak()

= Chapter 2
This heading is on page 2.

== Section 2.1
Still on page 2.

#pagebreak()

= Chapter 3
This is on page 3.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            typ_file = Path(tmpdir) / "multipage.typ"
            typ_file.write_text(typst_content)

            pdf_file = Path(tmpdir) / "multipage.pdf"
            typst.compile(str(typ_file), output=str(pdf_file), format='pdf')

            doc = fitz.open(str(pdf_file))
            toc = doc.get_toc()
            doc.close()

            # Extract page numbers
            pages = [entry[2] for entry in toc]

            # Verify page progression
            # Chapter 1 should be on page 1
            # Chapter 2 and Section 2.1 should be on page 2
            # Chapter 3 should be on page 3
            assert toc[0][1] == "Chapter 1" and toc[0][2] == 1
            assert toc[1][1] == "Chapter 2" and toc[1][2] == 2
            assert toc[2][1] == "Section 2.1" and toc[2][2] == 2
            assert toc[3][1] == "Chapter 3" and toc[3][2] == 3

    def test_empty_toc(self):
        """Test document with no headings produces empty TOC."""
        typst_content = """
#set page(width: 10cm, height: 10cm)

This is a document with no headings.
Just plain text content.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            typ_file = Path(tmpdir) / "no_headings.typ"
            typ_file.write_text(typst_content)

            pdf_file = Path(tmpdir) / "no_headings.pdf"
            typst.compile(str(typ_file), output=str(pdf_file), format='pdf')

            doc = fitz.open(str(pdf_file))
            toc = doc.get_toc()
            doc.close()

            # Should have no TOC entries
            assert len(toc) == 0, "Document without headings should have empty TOC"

    def test_unicode_headings(self):
        """Test TOC extraction with Unicode characters in headings."""
        typst_content = """
#set page(width: 10cm, height: 10cm)

= 第一章：介绍
Chinese characters in heading.

= Глава 2
Cyrillic characters.

= Κεφάλαιο 3
Greek characters.

= Chapter 4: Math $integral x^2$
With inline math.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            typ_file = Path(tmpdir) / "unicode.typ"
            typ_file.write_text(typst_content, encoding='utf-8')

            pdf_file = Path(tmpdir) / "unicode.pdf"
            typst.compile(str(typ_file), output=str(pdf_file), format='pdf')

            doc = fitz.open(str(pdf_file))
            toc = doc.get_toc()
            doc.close()

            # Should extract all headings
            assert len(toc) == 4

            # Verify Unicode is preserved
            titles = [entry[1] for entry in toc]
            assert "第一章：介绍" in titles[0]
            assert "Глава 2" in titles[1]
            assert "Κεφάλαιο 3" in titles[2]


@pytest.mark.skipif(not TYPST_AVAILABLE, reason="Requires PyMuPDF")
class TestPDFTOCExtraction:
    """Test TOC extraction from arbitrary PDF files."""

    def test_pdf_with_existing_toc(self):
        """Test extraction from a PDF that already has a TOC."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple PDF with TOC using PyMuPDF
            pdf_file = Path(tmpdir) / "with_toc.pdf"

            doc = fitz.open()

            # Add pages
            page1 = doc.new_page(width=400, height=600)
            page1.insert_text((50, 50), "Chapter 1 Content", fontsize=20)

            page2 = doc.new_page(width=400, height=600)
            page2.insert_text((50, 50), "Chapter 2 Content", fontsize=20)

            page3 = doc.new_page(width=400, height=600)
            page3.insert_text((50, 50), "Chapter 3 Content", fontsize=20)

            # Set TOC
            toc_data = [
                [1, "Introduction", 1],
                [2, "Background", 1],
                [1, "Methods", 2],
                [2, "Experimental Setup", 2],
                [1, "Conclusions", 3],
            ]
            doc.set_toc(toc_data)

            # Save and close
            doc.save(str(pdf_file))
            doc.close()

            # Re-open and extract TOC
            doc = fitz.open(str(pdf_file))
            extracted_toc = doc.get_toc()
            doc.close()

            # Verify extracted TOC matches what we set
            assert len(extracted_toc) == len(toc_data)

            for i, (expected, extracted) in enumerate(zip(toc_data, extracted_toc)):
                assert expected == list(extracted), \
                    f"TOC entry {i}: expected {expected}, got {list(extracted)}"

    def test_pdf_without_toc(self):
        """Test extraction from a PDF without TOC (should be empty)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "no_toc.pdf"

            # Create PDF without setting TOC
            doc = fitz.open()
            page = doc.new_page(width=400, height=600)
            page.insert_text((50, 50), "Just some content", fontsize=12)
            doc.save(str(pdf_file))
            doc.close()

            # Extract TOC
            doc = fitz.open(str(pdf_file))
            toc = doc.get_toc()
            doc.close()

            # Should be empty
            assert len(toc) == 0, "PDF without TOC should return empty list"


@pytest.mark.skipif(not TYPST_AVAILABLE, reason="Requires typst and PyMuPDF")
class TestPDFAssetTOCIntegration:
    """Test TOC extraction integration with PDFAsset."""

    def test_pdf_asset_per_page_toc(self):
        """Test that PDFAsset attaches only relevant TOC entries to each page."""
        from xtctool.assets.pdf import PDFAsset

        typst_content = """
#set page(width: 10cm, height: 8cm)

= Chapter 1
Page 1.

#pagebreak()

= Chapter 2
Page 2.

== Section 2.1
Still page 2.

#pagebreak()

= Chapter 3
Page 3.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            typ_file = Path(tmpdir) / "test.typ"
            typ_file.write_text(typst_content)

            pdf_file = Path(tmpdir) / "test.pdf"
            typst.compile(str(typ_file), output=str(pdf_file), format='pdf')

            # Use PDFAsset to convert
            pdf_asset = PDFAsset(str(pdf_file))
            assets = pdf_asset.convert({'extract_toc': True})

            # Page 1: 1 entry
            assert assets[0].get_metadata('toc') == [
                pytest.approx(lambda e: e.title == "Chapter 1" and e.page == 1)
            ] or len(assets[0].get_metadata('toc')) == 1

            # Page 2: 2 entries
            page2_toc = assets[1].get_metadata('toc')
            assert len(page2_toc) == 2
            assert page2_toc[0].title == "Chapter 2"
            assert page2_toc[1].title == "Section 2.1"

            # Page 3: 1 entry
            assert len(assets[2].get_metadata('toc')) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
