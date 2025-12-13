"""Test chapter preservation when concatenating XTC files."""

import tempfile
import pytest
from pathlib import Path

# Check if optional dependencies are available
try:
    import typst
    TYPST_AVAILABLE = True
except ImportError:
    TYPST_AVAILABLE = False


@pytest.mark.skipif(not TYPST_AVAILABLE, reason="Requires typst")
class TestXTCConcatenationChapters:
    """Test that chapters are preserved when concatenating XTC files."""

    def test_concat_two_xtc_preserves_chapters(self):
        """Test concatenating two XTC files preserves chapters from both."""
        from xtctool.assets.typst import TypstFileAsset
        from xtctool.assets.xtcontainer import XTContainerAsset
        from xtctool.cli.convert import write_xtc
        from xtctool.core.xtc import XTCReader

        typst1_content = """
#set page(width: 10cm, height: 8cm)

= Chapter 1
First document, chapter 1.

#pagebreak()

= Chapter 2
First document, chapter 2.
"""

        typst2_content = """
#set page(width: 10cm, height: 8cm)

= Chapter 3
Second document, chapter 3.

#pagebreak()

= Chapter 4
Second document, chapter 4.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            config = {'extract_toc': True, 'output': {'format': 'xth'}}

            # Create first XTC with 2 chapters
            typ1_file = tmpdir / "doc1.typ"
            typ1_file.write_text(typst1_content)

            typst1_asset = TypstFileAsset(str(typ1_file))
            # Pipeline: Typst → PDF → Images → Frames
            pdf1 = typst1_asset.convert(config)
            images1 = pdf1.convert(config)
            frames1 = []
            for img in images1:
                frames1.append(img.convert(config))

            xtc1_file = tmpdir / "doc1.xtc"
            write_xtc(str(xtc1_file), frames1, config)

            # Verify first XTC has 2 chapters
            reader1 = XTCReader()
            reader1.read(str(xtc1_file))
            assert len(reader1.chapters) == 2
            assert reader1.chapters[0].name == "Chapter 1"
            assert reader1.chapters[1].name == "Chapter 2"

            # Create second XTC with 2 chapters
            typ2_file = tmpdir / "doc2.typ"
            typ2_file.write_text(typst2_content)

            typst2_asset = TypstFileAsset(str(typ2_file))
            # Pipeline: Typst → PDF → Images → Frames
            pdf2 = typst2_asset.convert(config)
            images2 = pdf2.convert(config)
            frames2 = []
            for img in images2:
                frames2.append(img.convert(config))

            xtc2_file = tmpdir / "doc2.xtc"
            write_xtc(str(xtc2_file), frames2, config)

            # Verify second XTC has 2 chapters
            reader2 = XTCReader()
            reader2.read(str(xtc2_file))
            assert len(reader2.chapters) == 2
            assert reader2.chapters[0].name == "Chapter 3"
            assert reader2.chapters[1].name == "Chapter 4"

            # Concatenate the two XTCs
            xtc1_container = XTContainerAsset(str(xtc1_file))
            xtc2_container = XTContainerAsset(str(xtc2_file))

            concat_frames = []
            concat_frames.extend(xtc1_container.convert(config))
            concat_frames.extend(xtc2_container.convert(config))

            assert len(concat_frames) == 4

            # Write concatenated XTC
            concat_file = tmpdir / "concat.xtc"
            write_xtc(str(concat_file), concat_frames, config)

            # Read back and verify all 4 chapters are preserved
            reader_concat = XTCReader()
            reader_concat.read(str(concat_file))

            # REQUIREMENT: All chapters from both XTCs should be preserved
            assert len(reader_concat.chapters) == 4, \
                f"Expected 4 chapters (2 from each XTC), got {len(reader_concat.chapters)}"

            # Verify chapter names
            assert reader_concat.chapters[0].name == "Chapter 1"
            assert reader_concat.chapters[1].name == "Chapter 2"
            assert reader_concat.chapters[2].name == "Chapter 3"
            assert reader_concat.chapters[3].name == "Chapter 4"

            # Verify page numbers are adjusted (0-based)
            # XTC 1: pages 0-1
            assert reader_concat.chapters[0].start_page == 0
            assert reader_concat.chapters[0].end_page == 0
            assert reader_concat.chapters[1].start_page == 1
            assert reader_concat.chapters[1].end_page == 1

            # XTC 2: pages 2-3 (offset by 2)
            assert reader_concat.chapters[2].start_page == 2
            assert reader_concat.chapters[2].end_page == 2
            assert reader_concat.chapters[3].start_page == 3
            assert reader_concat.chapters[3].end_page == 3

    def test_concat_xtc_with_pdf_preserves_both_chapters(self):
        """Test concatenating XTC (with chapters) and PDF (with TOC) preserves both."""
        from xtctool.assets.typst import TypstFileAsset
        from xtctool.assets.xtcontainer import XTContainerAsset
        from xtctool.cli.convert import write_xtc
        from xtctool.core.xtc import XTCReader

        typst_content = """
#set page(width: 10cm, height: 8cm)

= XTC Chapter
From XTC file.

#pagebreak()

= PDF Chapter
From PDF converted to XTC.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            config = {'extract_toc': True, 'output': {'format': 'xth'}}

            # Create first XTC
            typ1_file = tmpdir / "doc1.typ"
            typ1_file.write_text(typst_content)

            typst1_asset = TypstFileAsset(str(typ1_file))
            # Pipeline: Typst → PDF → Images → Frames
            pdf1 = typst1_asset.convert(config)
            images1 = pdf1.convert(config)
            frames1 = []
            for img in images1:
                frames1.append(img.convert(config))

            xtc1_file = tmpdir / "doc1.xtc"
            write_xtc(str(xtc1_file), frames1, config)

            # Create second document from Typst (simulating PDF with TOC)
            typ2_file = tmpdir / "doc2.typ"
            typ2_file.write_text(typst_content)

            typst2_asset = TypstFileAsset(str(typ2_file))
            # Pipeline: Typst → PDF → Images → Frames
            pdf2 = typst2_asset.convert(config)
            images2 = pdf2.convert(config)
            frames2 = []
            for img in images2:
                frames2.append(img.convert(config))

            # Concatenate: XTC + newly converted frames
            xtc1_container = XTContainerAsset(str(xtc1_file))

            concat_frames = []
            concat_frames.extend(xtc1_container.convert(config))
            concat_frames.extend(frames2)

            # Write concatenated result
            concat_file = tmpdir / "concat.xtc"
            write_xtc(str(concat_file), concat_frames, config)

            # Verify all chapters preserved
            reader = XTCReader()
            reader.read(str(concat_file))

            # Should have chapters from both sources
            assert len(reader.chapters) == 4

    def test_concat_three_xtc_files(self):
        """Test concatenating three XTC files preserves all chapters with correct offsets."""
        from xtctool.assets.typst import TypstFileAsset
        from xtctool.assets.xtcontainer import XTContainerAsset
        from xtctool.cli.convert import write_xtc
        from xtctool.core.xtc import XTCReader

        # Simple single-chapter documents
        typst_template = """
#set page(width: 10cm, height: 8cm)

= Chapter {n}
Content for chapter {n}.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            config = {'extract_toc': True, 'output': {'format': 'xth'}}

            xtc_files = []
            for i in range(1, 4):  # Create 3 XTC files
                typ_file = tmpdir / f"doc{i}.typ"
                typ_file.write_text(typst_template.format(n=i))

                asset = TypstFileAsset(str(typ_file))
                # Pipeline: Typst → PDF → Images → Frames
                pdf = asset.convert(config)
                images = pdf.convert(config)
                frames = []
                for img in images:
                    frames.append(img.convert(config))

                xtc_file = tmpdir / f"doc{i}.xtc"
                write_xtc(str(xtc_file), frames, config)
                xtc_files.append(xtc_file)

            # Concatenate all three
            concat_frames = []
            for xtc_file in xtc_files:
                container = XTContainerAsset(str(xtc_file))
                concat_frames.extend(container.convert(config))

            # Write concatenated
            concat_file = tmpdir / "concat.xtc"
            write_xtc(str(concat_file), concat_frames, config)

            # Verify
            reader = XTCReader()
            reader.read(str(concat_file))

            assert len(reader.chapters) == 3
            assert reader.chapters[0].name == "Chapter 1"
            assert reader.chapters[0].start_page == 0
            assert reader.chapters[1].name == "Chapter 2"
            assert reader.chapters[1].start_page == 1
            assert reader.chapters[2].name == "Chapter 3"
            assert reader.chapters[2].start_page == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
