"""Markdown asset - converts Markdown to images via Typst templates."""

import logging
import tempfile
import shutil
from typing import Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from .base import FileAsset
from .image import ImageAsset

logger = logging.getLogger(__name__)


class MarkdownFileAsset(FileAsset):
    """Markdown file asset. Converts to ImageAsset by wrapping in Typst template.

    Markdown is rendered through Typst's native markdown support using #include.
    The markdown file is wrapped in a Jinja2 Typst template that can be customized
    with fonts, margins, and other styling options.
    """

    def convert(self, config: dict[str, Any]) -> list[ImageAsset]:
        """Render Markdown file to image asset(s) via Typst template.

        Args:
            config: Configuration dictionary

        Returns:
            List of ImageAsset objects (one per page)
        """
        from ..utils import TypstRenderer

        output_cfg = config.get('output', {})
        typst_cfg = config.get('typst', {})

        # Get dimensions and rendering settings
        width = output_cfg.get('width', 480)
        height = output_cfg.get('height', 800)
        ppi = typst_cfg.get('ppi', 144.0)

        # Calculate page dimensions in points (72 points = 1 inch)
        # Page size is calculated assuming 72 PPI base (1 pixel = 1 point)
        # Higher PPI values cause supersampling:
        #   ppi=72  -> 1x rendering (no supersampling)
        #   ppi=144 -> 2x rendering (960px rendered, downsampled to 480px)
        #   ppi=288 -> 4x rendering (1920px rendered, downsampled to 480px)
        # Downsampling creates anti-aliased pixels for better dithering quality
        width_pt = width  # Treat target pixels as points at 72 PPI
        height_pt = height

        # Get template settings
        template_dir = Path(__file__).parent.parent / 'templates'
        template_name = typst_cfg.get('template', 'default.typ.jinja')

        # Template variables (with sensible defaults)
        # Note: Boolean values need to be lowercase strings for Typst
        template_vars = {
            'width_pt': width_pt,
            'height_pt': height_pt,
            'width_px': width,
            'height_px': height,
            'ppi': ppi,
            'font': typst_cfg.get('font', 'Liberation Serif'),
            'font_size': typst_cfg.get('font_size', 24),
            'line_spacing': typst_cfg.get('line_spacing', 0.7),
            'justify': str(typst_cfg.get('justify', True)).lower(),
            'language': typst_cfg.get('language', 'en'),
            'margin_left': typst_cfg.get('margin_left', 16),
            'margin_right': typst_cfg.get('margin_right', 16),
            'margin_top': typst_cfg.get('margin_top', 24),
            'margin_bottom': typst_cfg.get('margin_bottom', 28),
            'list_spacing': typst_cfg.get('list_spacing', 8),
            'list_tight': str(typst_cfg.get('list_tight', False)).lower(),
            'show_page_numbers': str(typst_cfg.get('show_page_numbers', True)).lower(),
            'page_number_size': typst_cfg.get('page_number_size', 12),
            'show_toc': str(typst_cfg.get('show_toc', False)).lower(),
            'toc_title': typst_cfg.get('toc_title', 'Contents'),
        }

        # Create temporary working directory for multi-file rendering
        temp_dir = Path(tempfile.mkdtemp(prefix='markdown_'))

        try:
            # Copy markdown file to temp directory
            md_filename = Path(self.path).name
            temp_md_path = temp_dir / md_filename
            shutil.copy2(self.path, temp_md_path)

            # Load and render Jinja2 template
            jinja_env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=False
            )
            template = jinja_env.get_template(template_name)

            # Add markdown_file to template vars
            template_vars['markdown_file'] = md_filename

            typst_source = template.render(**template_vars)

            # Write rendered Typst source to temp directory
            typst_file = temp_dir / 'main.typ'
            typst_file.write_text(typst_source, encoding='utf-8')

            # Render using TypstRenderer with temp dir as root
            renderer = TypstRenderer(ppi=ppi)
            logger.info(f"Rendering Markdown file: {self.path}")
            images = renderer.render_file(str(typst_file), root_dir=str(temp_dir))

            return [ImageAsset(img) for img in images]

        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
