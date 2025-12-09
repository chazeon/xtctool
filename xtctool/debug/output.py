"""Debug output functions for decoding frames to PNG/PDF."""

import logging
from pathlib import Path
from typing import Any
from PIL import Image

from ..core.xth import XTHReader
from ..core.xtg import XTGReader

logger = logging.getLogger(__name__)


def decode_frame_to_image(frame) -> Image.Image:
    """Decode XTH/XTG frame back to PIL Image for debugging.

    Args:
        frame: FrameAsset to decode

    Returns:
        PIL Image object
    """
    if frame.format == 'xth':
        reader = XTHReader()
        return reader.decode(frame.data)
    else:  # xtg
        reader = XTGReader()
        return reader.decode(frame.data)


def write_png(output: str, frames: list, cfg: dict[str, Any]) -> None:
    """Decode frames and write as PNG files (for debugging).

    Args:
        output: Output file path
        frames: List of FrameAsset objects
        cfg: Configuration dictionary
    """
    if not frames:
        logger.warning("No frames to write")
        return

    output_path = Path(output)
    stem = output_path.stem
    parent = output_path.parent

    if len(frames) == 1:
        # Single frame
        img = decode_frame_to_image(frames[0])
        img.save(output, 'PNG')
        logger.info(f"Wrote: {output}")
    else:
        # Multiple frames - numbered files
        for idx, frame in enumerate(frames, 1):
            img = decode_frame_to_image(frame)
            out_file = parent / f"{stem}_{idx:03d}.png"
            img.save(str(out_file), 'PNG')
            logger.debug(f"Wrote: {out_file}")
        logger.info(f"Wrote {len(frames)} images to {parent / stem}_*.png")


def write_pdf(output: str, frames: list, cfg: dict[str, Any]) -> None:
    """Decode frames and write as multi-page PDF (for debugging).

    Args:
        output: Output file path
        frames: List of FrameAsset objects
        cfg: Configuration dictionary
    """
    if not frames:
        logger.warning("No frames to write")
        return

    # Decode all frames to images
    images = [decode_frame_to_image(frame) for frame in frames]

    # Convert to RGB for PDF
    rgb_images = [img.convert('RGB') for img in images]

    # Save as multi-page PDF with lossless compression
    # Use quality=100 and optimize=False to avoid JPEG artifacts
    save_kwargs = {
        'format': 'PDF',
        'quality': 100,
        'optimize': False,
    }

    if len(rgb_images) == 1:
        rgb_images[0].save(output, **save_kwargs)
    else:
        rgb_images[0].save(
            output,
            save_all=True,
            append_images=rgb_images[1:],
            **save_kwargs
        )

    logger.info(f"Wrote: {output} ({len(frames)} pages)")
