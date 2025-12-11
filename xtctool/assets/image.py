"""Image asset conversion logic."""

import logging
from typing import Any

from .base import ImageAsset as BaseImageAsset
from .xtframe import XTFrameAsset

logger = logging.getLogger(__name__)


class ImageAsset(BaseImageAsset):
    """Image asset with conversion to frame."""

    def _convert_impl(self, config: dict[str, Any]) -> XTFrameAsset:
        """Convert image to XTH or XTG frame.

        Args:
            config: Configuration dictionary

        Returns:
            XTFrameAsset (XTH or XTG)
        """
        from ..core.xth import XTHWriter
        from ..core.xtg import XTGWriter
        from PIL import Image

        output_cfg = config.get('output', {})
        width = output_cfg.get('width', 480)
        height = output_cfg.get('height', 800)
        format_type = output_cfg.get('format', 'xth').lower()

        if format_type not in ['xth', 'xtg']:
            raise ValueError(f"Invalid format '{format_type}'. Must be 'xth' or 'xtg'")

        # Get resample method from config
        resample_method_name = output_cfg.get('resample_method', 'BOX').upper()
        resample_method = getattr(Image.Resampling, resample_method_name, Image.Resampling.BOX)

        if format_type == 'xth':
            xth_cfg = config.get('xth', {})
            writer = XTHWriter(width, height)
            frame_data = writer.encode(
                self.image,
                thresholds=(
                    xth_cfg.get('threshold1', 85),
                    xth_cfg.get('threshold2', 170),
                    xth_cfg.get('threshold3', 255)
                ),
                invert=xth_cfg.get('invert', False),
                enable_dithering=xth_cfg.get('dither', True),
                dither_strength=xth_cfg.get('dither_strength', 0.8),
                resample_method=resample_method
            )
        else:  # xtg
            xtg_cfg = config.get('xtg', {})
            writer = XTGWriter(width, height)
            frame_data = writer.encode(
                self.image,
                threshold=xtg_cfg.get('threshold', 128),
                invert=xtg_cfg.get('invert', False),
                enable_dithering=xtg_cfg.get('dither', True),
                dither_strength=xtg_cfg.get('dither_strength', 0.8),
                resample_method=resample_method
            )

        return XTFrameAsset(frame_data, format_type)
