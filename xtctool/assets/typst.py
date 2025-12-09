"""Typst asset - converts Typst files to images."""

import logging
from typing import Any
from pathlib import Path

from .base import FileAsset
from .image import ImageAsset

logger = logging.getLogger(__name__)


class TypstFileAsset(FileAsset):
    """Typst file asset. Converts to ImageAsset by rendering.

    Supports multi-file Typst projects - #include directives will resolve
    relative to the .typ file's directory.
    """

    def convert(self, config: dict[str, Any]) -> list[ImageAsset]:
        """Render Typst file to image asset(s).

        Args:
            config: Configuration dictionary

        Returns:
            List of ImageAsset objects (one per page)
        """
        from ..utils import TypstRenderer

        typst_cfg = config.get('typst', {})
        ppi = typst_cfg.get('ppi', 144.0)

        renderer = TypstRenderer(ppi=ppi)

        # Get the directory containing the .typ file - used as root for #include
        root_dir = str(Path(self.path).parent)

        logger.info(f"Rendering Typst file: {self.path}")
        images = renderer.render_file(self.path, root_dir=root_dir)

        return [ImageAsset(img) for img in images]
