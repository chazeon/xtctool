"""Markdown asset - converts Markdown to images via Typst templates."""

import logging
import tempfile
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

    def _convert_impl(self, config: dict[str, Any]) -> list[ImageAsset]:
        """Render Markdown file to image asset(s) via Typst template.

        Args:
            config: Configuration dictionary

        Returns:
            List of ImageAsset objects (one per page)
        """
        output_cfg = config.get('output', {})
        typst_cfg = config.get('typst', {})

        # Get dimensions and rendering settings
        width = output_cfg.get('width', 480)
        height = output_cfg.get('height', 800)
        ppi = typst_cfg.get('ppi', 144.0)  # Kept for template variables

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
        template_spec = typst_cfg.get('template', 'default')

        # Determine if template_spec is a built-in name or a file path
        # Built-in: simple name like "default" (no path separator, no extension)
        # File path: has extension or path separator like "./default", "my.typ.jinja", "/path/to/template"
        is_builtin = ('/' not in template_spec and
                     '\\' not in template_spec and
                     '.' not in template_spec)

        if is_builtin:
            # Built-in template - look in package templates
            template_dir = Path(__file__).parent.parent / 'templates'
            template_name = f"{template_spec}.typ.jinja"
            logger.debug(f"Using built-in template: {template_name}")
        else:
            # File path - resolve relative to current working directory
            template_path = Path(template_spec).resolve()

            if not template_path.exists():
                raise FileNotFoundError(f"Template file not found: {template_spec} (resolved to {template_path})")

            template_dir = template_path.parent
            template_name = template_path.name
            logger.info(f"Using custom template: {template_path}")

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
            'line_spacing': typst_cfg.get('line_spacing', 0.5),
            'justify': str(typst_cfg.get('justify', True)).lower(),
            'language': typst_cfg.get('language', 'en'),
            'margin_left': typst_cfg.get('margin_left', 16),
            'margin_right': typst_cfg.get('margin_right', 16),
            'margin_top': typst_cfg.get('margin_top', 32),
            'margin_bottom': typst_cfg.get('margin_bottom', 32),
            'list_spacing': typst_cfg.get('list_spacing', 8),
            'list_tight': str(typst_cfg.get('list_tight', False)).lower(),
            'show_page_numbers': str(typst_cfg.get('show_page_numbers', True)).lower(),
            'page_number_style': typst_cfg.get('page_number_style', 'fraction'),
            'page_number_size': typst_cfg.get('page_number_size', 12),
            'show_toc': str(typst_cfg.get('show_toc', False)).lower(),
            'toc_title': typst_cfg.get('toc_title', 'Contents'),
        }

        # Create temporary Typst file in the markdown file's directory
        # This ensures Typst can find the markdown file and all its resources (images, etc.)
        markdown_path = Path(self.path).resolve()
        markdown_dir = markdown_path.parent

        # Create temp file in markdown's directory
        temp_typst = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.typ',
            dir=str(markdown_dir),
            delete=False,
            encoding='utf-8'
        )

        try:
            # Load and render Jinja2 template
            jinja_env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=False
            )
            template = jinja_env.get_template(template_name)

            # Use just the filename since typst file and markdown are in same directory
            template_vars['markdown_file'] = markdown_path.name

            typst_source = template.render(**template_vars)

            # Write rendered Typst source to temp file
            temp_typst.write(typst_source)
            temp_typst.close()

            # Compile Typst to PDF
            import typst
            from .pdf import PDFAsset

            temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            pdf_path = temp_pdf.name
            temp_pdf.close()

            try:
                logger.info(f"Compiling Markdown to PDF: {self.path}")
                typst.compile(
                    temp_typst.name,
                    output=pdf_path,
                    format='pdf',
                    root=str(markdown_dir)
                )

                # Use PDFAsset to convert PDF to images
                pdf_asset = PDFAsset(pdf_path)

                # Pass through page_spec metadata if present
                page_spec = self.get_metadata('page_spec')
                if page_spec:
                    pdf_asset.set_metadata('page_spec', page_spec)

                # Convert PDF to image assets (with TOC extraction)
                assets = pdf_asset.convert(config)

                return assets

            finally:
                # Clean up temp PDF
                Path(pdf_path).unlink(missing_ok=True)

        finally:
            # Clean up temp typst file
            Path(temp_typst.name).unlink(missing_ok=True)
