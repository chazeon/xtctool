"""Test Typst and Markdown asset rendering."""

import pytest
from pathlib import Path
import tempfile
from PIL import Image

from xtctool.assets import TypstFileAsset, MarkdownFileAsset, ImageAsset
from xtctool.utils import TypstRenderer


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        'output': {
            'width': 480,
            'height': 800,
        },
        'typst': {
            'ppi': 144.0,
            'font': 'Liberation Serif',
            'font_size': 11,
            'margin': 20,
        }
    }


@pytest.fixture
def sample_typst_file(tmp_path):
    """Create a sample Typst file for testing."""
    typst_content = """
#set page(width: 240pt, height: 400pt, margin: 10pt)
#set text(font: "Liberation Serif", size: 12pt)

= Test Document

This is a test Typst document.

- Item 1
- Item 2
- Item 3
"""
    typst_file = tmp_path / "test.typ"
    typst_file.write_text(typst_content, encoding='utf-8')
    return str(typst_file)


@pytest.fixture
def sample_markdown_file(tmp_path):
    """Create a sample Markdown file for testing."""
    markdown_content = """
# Test Markdown

This is a **test** markdown document with *italic* text.

## Section 1

- Item A
- Item B
- Item C

## Section 2

Some paragraph text here.
"""
    md_file = tmp_path / "test.md"
    md_file.write_text(markdown_content, encoding='utf-8')
    return str(md_file)


@pytest.fixture
def multi_file_typst_project(tmp_path):
    """Create a Typst project with multiple files and includes."""
    # Main file
    main_content = """
#set page(width: 240pt, height: 400pt, margin: 10pt)
#set text(font: "Liberation Serif", size: 12pt)

= Main Document

#include "chapter1.typ"

#include "chapter2.typ"
"""
    main_file = tmp_path / "main.typ"
    main_file.write_text(main_content, encoding='utf-8')

    # Chapter 1
    chapter1 = tmp_path / "chapter1.typ"
    chapter1.write_text("== Chapter 1\n\nContent of chapter 1.", encoding='utf-8')

    # Chapter 2
    chapter2 = tmp_path / "chapter2.typ"
    chapter2.write_text("== Chapter 2\n\nContent of chapter 2.", encoding='utf-8')

    return str(main_file)


class TestTypstRenderer:
    """Test the TypstRenderer utility."""

    def test_render_simple_source(self):
        """Test rendering simple Typst source."""
        renderer = TypstRenderer(ppi=144.0)
        source = '#set page(width: 240pt, height: 400pt)\n= Hello'

        image = renderer.render_source(source)

        assert isinstance(image, Image.Image)
        assert image.size[0] > 0
        assert image.size[1] > 0

    def test_render_file(self, sample_typst_file):
        """Test rendering Typst file."""
        renderer = TypstRenderer(ppi=144.0)

        images = renderer.render_file(sample_typst_file)

        assert isinstance(images, list)
        assert len(images) > 0
        assert isinstance(images[0], Image.Image)
        assert images[0].size[0] > 0
        assert images[0].size[1] > 0

    def test_render_nonexistent_file(self):
        """Test that rendering nonexistent file raises error."""
        renderer = TypstRenderer(ppi=144.0)

        with pytest.raises(FileNotFoundError):
            renderer.render_file("/nonexistent/file.typ")

    def test_render_multi_file_project(self, multi_file_typst_project):
        """Test rendering Typst project with includes."""
        renderer = TypstRenderer(ppi=144.0)

        # Should work because root_dir defaults to file's directory
        images = renderer.render_file(multi_file_typst_project)

        assert isinstance(images, list)
        assert len(images) > 0
        assert isinstance(images[0], Image.Image)
        assert images[0].size[0] > 0
        assert images[0].size[1] > 0


class TestTypstFileAsset:
    """Test TypstFileAsset conversion."""

    def test_convert_to_image_asset(self, sample_typst_file, test_config):
        """Test converting Typst file to ImageAsset(s)."""
        asset = TypstFileAsset(sample_typst_file)

        result = asset.convert(test_config)

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], ImageAsset)
        assert isinstance(result[0].image, Image.Image)
        assert result[0].image.size[0] > 0
        assert result[0].image.size[1] > 0

    def test_multi_file_project(self, multi_file_typst_project, test_config):
        """Test that multi-file Typst projects work."""
        asset = TypstFileAsset(multi_file_typst_project)

        result = asset.convert(test_config)

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], ImageAsset)


class TestMarkdownFileAsset:
    """Test MarkdownFileAsset conversion."""

    def test_convert_to_image_asset(self, sample_markdown_file, test_config):
        """Test converting Markdown file to ImageAsset(s) via Typst template."""
        asset = MarkdownFileAsset(sample_markdown_file)

        result = asset.convert(test_config)

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], ImageAsset)
        assert isinstance(result[0].image, Image.Image)
        assert result[0].image.size[0] > 0
        assert result[0].image.size[1] > 0

    def test_template_variables(self, sample_markdown_file, test_config):
        """Test that template variables are applied."""
        # Modify config with custom settings
        custom_config = test_config.copy()
        custom_config['typst'] = {
            'ppi': 144.0,
            'font': 'Liberation Serif',
            'font_size': 14,
            'margin': 30,
        }

        asset = MarkdownFileAsset(sample_markdown_file)
        result = asset.convert(custom_config)

        # Should succeed with custom settings
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], ImageAsset)

    def test_default_template(self, sample_markdown_file, test_config):
        """Test that default template works."""
        asset = MarkdownFileAsset(sample_markdown_file)

        result = asset.convert(test_config)

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], ImageAsset)
        assert result[0].image.mode in ['RGB', 'RGBA', 'L']


class TestTemplateIntegration:
    """Test that templates are correctly integrated."""

    def test_default_template_exists(self):
        """Test that default.typ.jinja template exists."""
        from pathlib import Path

        template_dir = Path(__file__).parent.parent / 'xtctool' / 'templates'
        default_template = template_dir / 'default.typ.jinja'

        assert template_dir.exists(), "Templates directory should exist"
        assert default_template.exists(), "default.typ.jinja should exist"

    def test_template_renders_markdown(self, sample_markdown_file, test_config):
        """Test that template correctly includes and renders markdown."""
        asset = MarkdownFileAsset(sample_markdown_file)
        result = asset.convert(test_config)

        # The result should be rendered successfully
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], ImageAsset)
        assert result[0].image.size[0] > 0
        assert result[0].image.size[1] > 0
