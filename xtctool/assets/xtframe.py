"""Frame assets - XTH/XTG final format."""

import tempfile
import os
import logging
from typing import Any, Optional

from .base import Asset, FileAsset

logger = logging.getLogger(__name__)


class XTFrameAsset(Asset):
    """XTH/XTG frame asset. Final format - no further conversion."""

    def __init__(self, data: bytes, format: str):
        """Initialize frame asset.

        Args:
            data: Frame data bytes
            format: 'xth' or 'xtg'
        """
        self.data = data
        self.format = format
        self._temp_file: Optional[str] = None

    def as_bytes(self) -> bytes:
        return self.data

    def as_file(self) -> str:
        """Write to temp file and return path."""
        if self._temp_file is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{self.format}') as tmp:
                tmp.write(self.data)
                self._temp_file = tmp.name
        return self._temp_file

    def cleanup(self) -> None:
        if self._temp_file and os.path.exists(self._temp_file):
            os.unlink(self._temp_file)
            self._temp_file = None

    def convert(self, config: dict[str, Any]) -> 'XTFrameAsset':
        """Frame is final format - returns self."""
        return self


class FileXTFrameAsset(FileAsset):
    """XTH/XTG file asset. Converts to XTFrameAsset by reading file."""

    def __init__(self, path: str):
        super().__init__(path, is_temp=False)
        # Detect format from extension
        ext = os.path.splitext(path)[1].lower()
        self.format = ext[1:] if ext in ['.xth', '.xtg'] else 'xth'

    def convert(self, config: dict[str, Any]) -> XTFrameAsset:
        """Read file and convert to XTFrameAsset."""
        data = self.as_bytes()
        return XTFrameAsset(data, self.format)


# Backwards compatibility aliases
FrameAsset = XTFrameAsset
FileFrameAsset = FileXTFrameAsset
