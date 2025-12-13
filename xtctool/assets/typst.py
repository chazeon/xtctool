"""Typst asset - converts Typst files to PDF."""

import logging
import tempfile
from typing import Any
from pathlib import Path

from .base import FileAsset
from .pdf import PDFAsset

logger = logging.getLogger(__name__)


class TypstFileAsset(FileAsset):
    """Typst file asset. Converts to PDFAsset.

    Supports multi-file Typst projects - #include directives will resolve
    relative to the .typ file's directory.
    """

    def _convert_impl(self, config: dict[str, Any]) -> PDFAsset:
        """Compile Typst file to PDF asset.

        Args:
            config: Configuration dictionary

        Returns:
            PDFAsset object
        """
        import typst

        # Get the directory containing the .typ file - used as root for #include
        root_dir = str(Path(self.path).parent)

        logger.info(f"Compiling Typst to PDF: {self.path}")

        # Create temporary PDF file
        temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        pdf_path = temp_pdf.name
        temp_pdf.close()

        # Compile Typst to PDF
        typst.compile(
            self.path,
            output=pdf_path,
            format='pdf',
            root=root_dir
        )

        # Return PDFAsset (pipeline will convert to images automatically)
        return PDFAsset(pdf_path, is_temp=True)
