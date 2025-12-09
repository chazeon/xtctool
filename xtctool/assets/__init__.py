"""Asset classes for conversion pipeline."""

from .base import Asset, MemoryAsset, FileAsset
from .image import ImageAsset
from .pdf import PDFAsset
from .xtframe import XTFrameAsset, FrameAsset, FileXTFrameAsset, FileFrameAsset
from .xtcontainer import XTContainerAsset
from .typst import TypstFileAsset
from .markdown import MarkdownFileAsset

__all__ = [
    'Asset',
    'MemoryAsset',
    'FileAsset',
    'ImageAsset',
    'PDFAsset',
    'XTFrameAsset',
    'FrameAsset',  # Backwards compatibility
    'FileXTFrameAsset',
    'FileFrameAsset',  # Backwards compatibility
    'XTContainerAsset',
    'TypstFileAsset',
    'MarkdownFileAsset',
]
