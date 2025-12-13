"""Typst asset - converts Typst files to images via PDF."""

import logging
import tempfile
from typing import Any
from pathlib import Path

from .base import FileAsset
from .image import ImageAsset
from .pdf import PDFAsset

logger = logging.getLogger(__name__)


class TypstFileAsset(FileAsset):
    """Typst file asset. Converts to ImageAsset by rendering via PDF.

    Supports multi-file Typst projects - #include directives will resolve
    relative to the .typ file's directory.
    """

    def _convert_impl(self, config: dict[str, Any]) -> list[ImageAsset]:
        """Render Typst file to image asset(s) via PDF.

        Args:
            config: Configuration dictionary

        Returns:
            List of ImageAsset objects (one per page)
        """
        import typst

        # Get the directory containing the .typ file - used as root for #include
        root_dir = str(Path(self.path).parent)

        logger.info(f"Compiling Typst to PDF: {self.path}")

        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            pdf_path = tmp_pdf.name

        try:
            # Compile Typst to PDF
            typst.compile(
                self.path,
                output=pdf_path,
                format='pdf',
                root=root_dir
            )

            # Use PDFAsset to convert PDF to images
            pdf_asset = PDFAsset(pdf_path)

            # Pass through page_spec metadata if present
            page_spec = self.get_metadata('page_spec')
            if page_spec:
                pdf_asset.set_metadata('page_spec', page_spec)

            # Convert PDF to image assets (with TOC extraction)
            # PDFAsset will use config['pdf']['resolution'] if set
            assets = pdf_asset.convert(config)

            return assets

        finally:
            # Clean up temporary PDF
            Path(pdf_path).unlink(missing_ok=True)
