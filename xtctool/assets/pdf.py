"""PDF asset - converts PDF to images."""

import logging
from typing import Any
from itertools import groupby
from tqdm.auto import tqdm

from .base import FileAsset
from .image import ImageAsset

logger = logging.getLogger(__name__)


class PDFAsset(FileAsset):
    """PDF file asset. Converts to list of ImageAssets (one per page)."""

    def _convert_impl(self, config: dict[str, Any]) -> list[ImageAsset]:
        """Convert PDF pages to image assets.

        Args:
            config: Configuration dictionary

        Returns:
            List of ImageAsset objects (one per page)
        """
        from ..utils import PDFConverter, parse_page_range
        from pathlib import Path

        pdf_cfg = config.get('pdf', {})
        resolution = pdf_cfg.get('resolution', 144)

        converter = PDFConverter(resolution=resolution)
        page_count = converter.get_page_count(self.path)
        pdf_name = Path(self.path).name

        # Extract TOC if enabled and group by page
        toc_by_page = {}
        if config.get('extract_toc', True):
            toc = converter.extract_toc(self.path)
            if toc:
                logger.info(f"PDF: Extracted {len(toc)} TOC entries from {pdf_name}")
                # Group TOC entries by page number for efficient lookup
                for page, entries in groupby(toc, key=lambda e: e.page):
                    toc_by_page[page] = list(entries)

        # Check for page selection in metadata
        page_spec = self.get_metadata('page_spec')
        if page_spec:
            pages = parse_page_range(page_spec, page_count)
            logger.info(f"PDF: Rendering {len(pages)} of {page_count} pages from {self.path} (pages: {page_spec})")
        else:
            pages = range(1, page_count + 1)
            logger.info(f"PDF: {page_count} pages from {self.path}")

        assets = []
        for page_num in tqdm(
            pages,
            desc=f"  Rendering {pdf_name}",
            unit="page",
            leave=False,
            disable=None
        ):
            image = converter.render_page(self.path, page_num)
            image_asset = ImageAsset(image)

            # Attach TOC entries for this page
            page_toc = toc_by_page.get(page_num)
            if page_toc:
                image_asset.set_metadata('toc', page_toc)

            assets.append(image_asset)

        return assets
