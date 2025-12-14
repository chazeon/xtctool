"""End-to-end test for TOC extraction → XTC chapters."""

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
class TestTOCToXTCPipeline:
    """Test full pipeline from Typst/Markdown → PDF → TOC → XTC chapters."""

    def test_typst_to_xtc_with_chapters(self):
        """Test Typst file with headings produces XTC with chapters."""
        from xtctool.assets.typst import TypstFileAsset
        from xtctool.cli.convert import extract_chapters_from_toc, write_xtc
        from xtctool.core.xtc import XTCReader

        typst_content = """
#set page(width: 10cm, height: 8cm)

= Chapter 1
First chapter content.

#pagebreak()

= Chapter 2
Second chapter content.

== Section 2.1
Subsection.

#pagebreak()

= Chapter 3
Third chapter content.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Typst file
            typ_file = Path(tmpdir) / "test.typ"
            typ_file.write_text(typst_content)

            # Convert through pipeline: Typst → PDF → Images → Frames
            typst_asset = TypstFileAsset(str(typ_file))
            config = {'extract_toc': True, 'output': {'format': 'xth'}}

            # Step 1: Typst → PDF
            pdf_asset = typst_asset.convert(config)

            # Step 2: PDF → Images
            image_assets = pdf_asset.convert(config)
            assert len(image_assets) == 3  # 3 pages

            # Step 3: Images → Frames
            frames = []
            for img_asset in image_assets:
                frame = img_asset.convert(config)
                frames.append(frame)

            # Extract chapters
            chapters = extract_chapters_from_toc(frames)

            # Verify chapters were extracted
            assert len(chapters) == 3
            assert chapters[0].name == "Chapter 1"
            assert chapters[0].start_page == 0
            assert chapters[0].end_page == 0  # Page 1 only

            assert chapters[1].name == "Chapter 2"
            assert chapters[1].start_page == 1
            assert chapters[1].end_page == 1  # Page 2 only

            assert chapters[2].name == "Chapter 3"
            assert chapters[2].start_page == 2
            assert chapters[2].end_page == 2  # Page 3 (last page)

            # Write XTC file
            xtc_file = Path(tmpdir) / "output.xtc"
            write_xtc(str(xtc_file), frames, config)

            # Read back and verify chapters
            reader = XTCReader()
            reader.read(str(xtc_file))

            assert len(reader.chapters) == 3
            assert reader.chapters[0].name == "Chapter 1"
            assert reader.chapters[1].name == "Chapter 2"
            assert reader.chapters[2].name == "Chapter 3"

    def test_markdown_to_xtc_with_chapters(self):
        """Test Markdown file with headings produces XTC with chapters."""
        from xtctool.assets.markdown import MarkdownFileAsset
        from xtctool.cli.convert import extract_chapters_from_toc
        from xtctool.core.xtc import XTCReader

        markdown_content = """# Introduction

This is the introduction.

# Methods

This is the methods section.

# Results

This is the results section.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Markdown file
            md_file = Path(tmpdir) / "test.md"
            md_file.write_text(markdown_content)

            # Convert through pipeline: Markdown → PDF → Images → Frames
            md_asset = MarkdownFileAsset(str(md_file))
            config = {'extract_toc': True, 'output': {'format': 'xth', 'height': 600}}

            # Step 1: Markdown → PDF
            pdf_asset = md_asset.convert(config)

            # Step 2: PDF → Images
            image_assets = pdf_asset.convert(config)

            # Step 3: Images → Frames
            frames = []
            for img_asset in image_assets:
                frame = img_asset.convert(config)
                frames.append(frame)

            # Extract chapters
            chapters = extract_chapters_from_toc(frames)

            # Verify chapters (Markdown h1 → Typst level-1 heading)
            assert len(chapters) == 3
            assert chapters[0].name == "Introduction"
            assert chapters[1].name == "Methods"
            assert chapters[2].name == "Results"

    def test_pdf_to_xtc_with_chapters(self):
        """Test PDF with TOC produces XTC with chapters."""
        from xtctool.assets.pdf import PDFAsset
        from xtctool.cli.convert import extract_chapters_from_toc

        # Create a simple PDF with TOC using Typst
        typst_content = """
#set page(width: 10cm, height: 10cm)

= Chapter A
Content A.

#pagebreak()

= Chapter B
Content B.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            typ_file = Path(tmpdir) / "test.typ"
            typ_file.write_text(typst_content)

            pdf_file = Path(tmpdir) / "test.pdf"
            typst.compile(str(typ_file), output=str(pdf_file), format='pdf')

            # Convert PDF to frames
            pdf_asset = PDFAsset(str(pdf_file))
            config = {'extract_toc': True, 'output': {'format': 'xth'}}
            image_assets = pdf_asset.convert(config)

            frames = []
            for img_asset in image_assets:
                frame = img_asset.convert(config)
                frames.append(frame)

            # Extract chapters
            chapters = extract_chapters_from_toc(frames)

            assert len(chapters) == 2
            assert chapters[0].name == "Chapter A"
            assert chapters[0].start_page == 0
            assert chapters[0].end_page == 0

            assert chapters[1].name == "Chapter B"
            assert chapters[1].start_page == 1
            assert chapters[1].end_page == 1

    def test_no_toc_produces_no_chapters(self):
        """Test document without headings produces no chapters."""
        from xtctool.assets.typst import TypstFileAsset
        from xtctool.cli.convert import extract_chapters_from_toc

        typst_content = """
#set page(width: 10cm, height: 10cm)

This is a document with no headings.
Just plain text.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            typ_file = Path(tmpdir) / "test.typ"
            typ_file.write_text(typst_content)

            typst_asset = TypstFileAsset(str(typ_file))
            config = {'extract_toc': True, 'output': {'format': 'xth'}}

            # Pipeline: Typst → PDF → Images → Frames
            pdf_asset = typst_asset.convert(config)
            image_assets = pdf_asset.convert(config)

            frames = []
            for img_asset in image_assets:
                frame = img_asset.convert(config)
                frames.append(frame)

            # No chapters should be extracted
            chapters = extract_chapters_from_toc(frames)
            assert len(chapters) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
