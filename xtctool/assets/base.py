"""Base asset classes for conversion pipeline."""

from abc import ABC, abstractmethod
from typing import Any, Optional
import tempfile
import os
import logging

logger = logging.getLogger(__name__)


class Asset(ABC):
    """Base class for all assets."""

    @abstractmethod
    def as_bytes(self) -> bytes:
        """Get asset data as bytes."""
        pass

    @abstractmethod
    def as_file(self) -> str:
        """Get asset as file path (may create temp file)."""
        pass

    def cleanup(self) -> None:
        """Clean up any temporary resources."""
        pass

    def __del__(self):
        """Auto cleanup on destruction."""
        self.cleanup()

    def convert(self, config: dict[str, Any]) -> Any:
        """Convert this asset to its next stage.

        Override in subclasses to define conversion path.
        Default: no conversion (final format).

        Args:
            config: Configuration dictionary

        Returns:
            Converted asset(s) or self
        """
        return self


class MemoryAsset(Asset):
    """Asset stored in memory as bytes."""

    def __init__(self, data: bytes):
        self.data = data
        self._temp_file: Optional[str] = None

    def as_bytes(self) -> bytes:
        return self.data

    def as_file(self) -> str:
        """Write to temp file and return path."""
        if self._temp_file is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.dat') as tmp:
                tmp.write(self.data)
                self._temp_file = tmp.name
        return self._temp_file

    def cleanup(self) -> None:
        if self._temp_file and os.path.exists(self._temp_file):
            os.unlink(self._temp_file)
            self._temp_file = None


class FileAsset(Asset):
    """Asset backed by a file on disk."""

    def __init__(self, path: str, is_temp: bool = False):
        self.path = path
        self.is_temp = is_temp

    def as_bytes(self) -> bytes:
        with open(self.path, 'rb') as f:
            return f.read()

    def as_file(self) -> str:
        return self.path

    def cleanup(self) -> None:
        if self.is_temp and os.path.exists(self.path):
            os.unlink(self.path)


class ImageAsset(Asset):
    """Asset wrapping a PIL Image."""

    def __init__(self, image):  # image: PIL.Image.Image
        self.image = image
        self._temp_file: Optional[str] = None

    def as_bytes(self) -> bytes:
        """Get as PNG bytes."""
        import io
        buf = io.BytesIO()
        self.image.save(buf, format='PNG')
        return buf.getvalue()

    def as_file(self) -> str:
        """Save to temp PNG file."""
        if self._temp_file is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                self._temp_file = tmp.name
            self.image.save(self._temp_file, 'PNG')
        return self._temp_file

    def cleanup(self) -> None:
        if self._temp_file and os.path.exists(self._temp_file):
            os.unlink(self._temp_file)
            self._temp_file = None
