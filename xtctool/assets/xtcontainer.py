"""XTC container asset conversion logic."""

import logging
import struct
from typing import Any

from .base import FileAsset
from .xtframe import XTFrameAsset

logger = logging.getLogger(__name__)


class XTContainerAsset(FileAsset):
    """XTC container asset - extracts individual XTH/XTG frames."""

    def _convert_impl(self, config: dict[str, Any]) -> list[XTFrameAsset]:
        """Extract frames from XTC container.

        Args:
            config: Configuration dictionary (unused)

        Returns:
            List of XTFrameAsset objects (one per page)
        """
        from ..core.xtc import XTCReader

        reader = XTCReader()
        frame_data_list = reader.read(self.path)

        # Determine format from first frame's magic number
        if frame_data_list:
            magic = struct.unpack('<I', frame_data_list[0][0:4])[0]
            if magic == 0x00485458:  # "XTH\0"
                format_type = 'xth'
            elif magic == 0x00475458:  # "XTG\0"
                format_type = 'xtg'
            else:
                raise ValueError(f"Unknown frame format in XTC: {magic:#x}")
        else:
            raise ValueError("XTC file contains no frames")

        # Apply page selection if specified in metadata
        page_spec = self.get_metadata('page_spec')
        if page_spec:
            from ..utils import parse_page_range
            pages = parse_page_range(page_spec, len(frame_data_list))
            frame_data_list = [frame_data_list[i-1] for i in pages]
            logger.info(f"Selected {len(frame_data_list)} {format_type.upper()} frames from XTC (pages: {page_spec})")
        else:
            logger.info(f"Extracted {len(frame_data_list)} {format_type.upper()} frames from XTC")

        # Create XTFrameAsset for each frame
        assets = []
        for data in frame_data_list:
            asset = XTFrameAsset(data, format_type)
            assets.append(asset)

        return assets
