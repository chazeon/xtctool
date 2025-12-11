"""Test metadata propagation system."""

import pytest
from pathlib import Path
import tempfile
from PIL import Image

from xtctool.assets import (
    Asset, ImageAsset, PDFAsset, MarkdownFileAsset,
    TypstFileAsset, XTContainerAsset
)
from xtctool.assets.base import MemoryAsset


class TestMetadataBasics:
    """Test basic metadata operations on Asset base class."""

    def test_set_and_get_metadata(self):
        """Test setting and getting metadata."""
        asset = MemoryAsset(b'test data')
        asset.set_metadata('key', 'value')
        assert asset.get_metadata('key') == 'value'

    def test_get_nonexistent_metadata(self):
        """Test getting nonexistent metadata returns None."""
        asset = MemoryAsset(b'test data')
        assert asset.get_metadata('nonexistent') is None

    def test_get_metadata_with_default(self):
        """Test getting metadata with default value."""
        asset = MemoryAsset(b'test data')
        assert asset.get_metadata('missing', default='default') == 'default'

    def test_multiple_metadata_values(self):
        """Test setting multiple metadata values."""
        asset = MemoryAsset(b'test data')
        asset.set_metadata('key1', 'value1')
        asset.set_metadata('key2', 'value2')
        asset.set_metadata('key3', 123)

        assert asset.get_metadata('key1') == 'value1'
        assert asset.get_metadata('key2') == 'value2'
        assert asset.get_metadata('key3') == 123

    def test_overwrite_metadata(self):
        """Test overwriting metadata value."""
        asset = MemoryAsset(b'test data')
        asset.set_metadata('key', 'old_value')
        asset.set_metadata('key', 'new_value')
        assert asset.get_metadata('key') == 'new_value'


class TestMetadataPropagation:
    """Test metadata propagation between assets."""

    def test_propagate_to_new_asset(self):
        """Test propagating metadata to another asset."""
        source = MemoryAsset(b'source data')
        source.set_metadata('page_spec', '1-4')
        source.set_metadata('custom', 'value')

        target = MemoryAsset(b'target data')
        source.propagate_metadata(target)

        assert target.get_metadata('page_spec') == '1-4'
        assert target.get_metadata('custom') == 'value'

    def test_propagate_empty_metadata(self):
        """Test propagating from asset with no metadata."""
        source = MemoryAsset(b'source data')
        target = MemoryAsset(b'target data')
        target.set_metadata('existing', 'value')

        source.propagate_metadata(target)

        # Target should keep its existing metadata
        assert target.get_metadata('existing') == 'value'

    def test_propagate_overwrites_target(self):
        """Test that propagate updates existing keys in target."""
        source = MemoryAsset(b'source data')
        source.set_metadata('key', 'source_value')

        target = MemoryAsset(b'target data')
        target.set_metadata('key', 'target_value')

        source.propagate_metadata(target)

        # Source value should overwrite target value
        assert target.get_metadata('key') == 'source_value'

    def test_propagate_preserves_source(self):
        """Test that propagation doesn't modify source."""
        source = MemoryAsset(b'source data')
        source.set_metadata('key', 'value')

        target = MemoryAsset(b'target data')
        source.propagate_metadata(target)

        # Modify target
        target.set_metadata('key', 'modified')

        # Source should be unchanged
        assert source.get_metadata('key') == 'value'


class TestPageSpecMetadata:
    """Test page_spec metadata specifically."""

    def test_page_spec_on_image_asset(self):
        """Test setting page_spec on ImageAsset."""
        img = Image.new('RGB', (100, 100), color='white')
        asset = ImageAsset(img)
        asset.set_metadata('page_spec', '1-3')

        assert asset.get_metadata('page_spec') == '1-3'

    def test_page_spec_propagation_chain(self):
        """Test page_spec propagates through a chain of assets."""
        # Create chain: asset1 → asset2 → asset3
        asset1 = MemoryAsset(b'data1')
        asset1.set_metadata('page_spec', '5-10')

        asset2 = MemoryAsset(b'data2')
        asset1.propagate_metadata(asset2)

        asset3 = MemoryAsset(b'data3')
        asset2.propagate_metadata(asset3)

        # page_spec should propagate through entire chain
        assert asset3.get_metadata('page_spec') == '5-10'


class TestMetadataInConversion:
    """Test metadata propagation during actual conversions."""

    @pytest.fixture
    def test_config(self):
        """Minimal config for testing."""
        return {
            'output': {'width': 480, 'height': 800, 'format': 'xth'},
            'typst': {'ppi': 144.0},
            'pdf': {'resolution': 144},
        }

    def test_image_asset_propagates_metadata(self, test_config, tmp_path):
        """Test ImageAsset propagates metadata when converting."""
        # Create a simple image
        img = Image.new('RGB', (480, 800), color='white')
        asset = ImageAsset(img)
        asset.set_metadata('page_spec', '1-3')
        asset.set_metadata('custom_key', 'custom_value')

        # Convert to XTFrame
        result = asset.convert(test_config)

        # Metadata should propagate to result
        assert result.get_metadata('page_spec') == '1-3'
        assert result.get_metadata('custom_key') == 'custom_value'

    def test_typst_propagates_metadata(self, test_config, tmp_path):
        """Test TypstFileAsset propagates metadata to output images."""
        # Create a simple Typst file
        typst_content = """
#set page(width: 240pt, height: 400pt)
#set text(size: 12pt)

= Page 1
Content for page 1.

#pagebreak()

= Page 2
Content for page 2.
"""
        typst_file = tmp_path / "test.typ"
        typst_file.write_text(typst_content, encoding='utf-8')

        # Create asset with metadata
        asset = TypstFileAsset(str(typst_file))
        asset.set_metadata('custom', 'test_value')

        # Convert (should produce ImageAssets)
        results = asset.convert(test_config)

        # All resulting ImageAssets should have the metadata
        assert len(results) > 0
        for img_asset in results:
            assert img_asset.get_metadata('custom') == 'test_value'

    def test_markdown_propagates_metadata(self, test_config, tmp_path):
        """Test MarkdownFileAsset propagates metadata to output images."""
        # Create a simple Markdown file
        md_content = """# Test Document

This is a test markdown document.

- Item 1
- Item 2
- Item 3

## Section 2

More content here.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding='utf-8')

        # Create asset with metadata
        asset = MarkdownFileAsset(str(md_file))
        asset.set_metadata('page_spec', '1')
        asset.set_metadata('source', 'markdown')

        # Convert (should produce ImageAssets)
        results = asset.convert(test_config)

        # All resulting ImageAssets should have the metadata
        assert len(results) > 0
        for img_asset in results:
            assert img_asset.get_metadata('page_spec') == '1'
            assert img_asset.get_metadata('source') == 'markdown'


class TestPageSpecFiltering:
    """Test that page_spec metadata actually filters pages during conversion."""

    @pytest.fixture
    def test_config(self):
        """Minimal config for testing."""
        return {
            'output': {'width': 480, 'height': 800, 'format': 'xth'},
            'typst': {'ppi': 144.0},
        }

    def test_typst_page_selection(self, test_config, tmp_path):
        """Test TypstFileAsset respects page_spec metadata."""
        # Create a multi-page Typst document
        typst_content = """
#set page(width: 240pt, height: 400pt)
#set text(size: 12pt)

= Page 1
#pagebreak()
= Page 2
#pagebreak()
= Page 3
#pagebreak()
= Page 4
"""
        typst_file = tmp_path / "test.typ"
        typst_file.write_text(typst_content, encoding='utf-8')

        # Convert without page_spec - should get all pages
        asset_all = TypstFileAsset(str(typst_file))
        results_all = asset_all.convert(test_config)
        assert len(results_all) == 4

        # Convert with page_spec - should get only selected pages
        asset_subset = TypstFileAsset(str(typst_file))
        asset_subset.set_metadata('page_spec', '1,3')
        results_subset = asset_subset.convert(test_config)
        assert len(results_subset) == 2

    def test_markdown_page_selection(self, test_config, tmp_path):
        """Test MarkdownFileAsset respects page_spec metadata."""
        # Create a document that will span multiple pages
        md_content = """# Page 1

""" + "\n\n".join([f"Paragraph {i}" for i in range(50)])

        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding='utf-8')

        # Convert without page_spec
        asset_all = MarkdownFileAsset(str(md_file))
        results_all = asset_all.convert(test_config)
        total_pages = len(results_all)

        # Convert with page_spec to get first page only
        asset_subset = MarkdownFileAsset(str(md_file))
        asset_subset.set_metadata('page_spec', '1')
        results_subset = asset_subset.convert(test_config)

        # Should get exactly 1 page
        assert len(results_subset) == 1
        assert len(results_subset) < total_pages


class TestMetadataIsolation:
    """Test that metadata changes don't leak between conversions."""

    def test_multiple_conversions_independent(self):
        """Test that converting same asset twice with different metadata is independent."""
        asset1 = MemoryAsset(b'data1')
        asset1.set_metadata('key', 'value1')

        asset2 = MemoryAsset(b'data2')
        asset2.set_metadata('key', 'value2')

        # Metadata should be independent
        assert asset1.get_metadata('key') == 'value1'
        assert asset2.get_metadata('key') == 'value2'
