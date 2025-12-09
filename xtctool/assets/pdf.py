"""PDF asset - converts PDF to images."""

import logging
from typing import Any
from tqdm.auto import tqdm

from .base import FileAsset
from .image import ImageAsset

logger = logging.getLogger(__name__)


class PDFAsset(FileAsset):
    """PDF file asset. Converts to list of ImageAssets (one per page)."""

    def convert(self, config: dict[str, Any]) -> list[ImageAsset]:
        """Convert PDF pages to image assets.

        Args:
            config: Configuration dictionary

        Returns:
            List of ImageAsset objects (one per page)
        """
        from ..utils import PDFConverter
        from pathlib import Path

        pdf_cfg = config.get('pdf', {})
        resolution = pdf_cfg.get('resolution', 144)

        converter = PDFConverter(resolution=resolution)
        page_count = converter.get_page_count(self.path)
        pdf_name = Path(self.path).name
        logger.info(f"PDF: {page_count} pages from {self.path}")

        assets = []
        for page_num in tqdm(
            range(1, page_count + 1),
            desc=f"  Rendering {pdf_name}",
            unit="page",
            leave=False,
            disable=None
        ):
            image = converter.render_page(self.path, page_num)
            assets.append(ImageAsset(image))

        return assets
