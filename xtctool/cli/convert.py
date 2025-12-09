"""Queue-based file conversion pipeline."""

import click
import logging
import tomllib
from collections import deque
from pathlib import Path
from typing import Any, Optional
from tqdm.auto import tqdm

from ..assets import PDFAsset, ImageAsset, XTFrameAsset, FileXTFrameAsset, XTContainerAsset
from ..debug import output as debug_output

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    'output': {
        'width': 480,
        'height': 800,
        'title': '',
        'author': '',
        'publisher': '',
        'language': 'en-US',
        'direction': 'ltr',
    },
    'pdf': {'resolution': 144},
    'xth': {
        'threshold1': 85,
        'threshold2': 170,
        'threshold3': 255,
        'invert': False,
        'dither': True,
        'dither_strength': 0.8,
    },
    'xtg': {
        'threshold': 128,
        'invert': False,
        'dither': True,
        'dither_strength': 0.8,
    },
    'typst': {'ppi': 144.0},
}


def load_config(config_path: Optional[str]) -> dict[str, Any]:
    """Load configuration from TOML file or use defaults."""
    if config_path is None:
        return DEFAULT_CONFIG

    try:
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
        logger.info(f"Loaded config: {config_path}")

        # Merge with defaults
        merged = DEFAULT_CONFIG.copy()
        for section, values in config.items():
            if section in merged:
                merged[section].update(values)
            else:
                merged[section] = values
        return merged
    except FileNotFoundError:
        logger.error(f"Config not found: {config_path}")
        raise click.BadParameter(f"Config not found: {config_path}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise click.BadParameter(f"Failed to load config: {e}")


def create_asset(path: str):
    """Create appropriate asset from file path."""
    p = Path(path)
    ext = p.suffix.lower()

    if ext == '.pdf':
        return PDFAsset(path)
    elif ext in ['.png', '.jpg', '.jpeg']:
        from PIL import Image
        img = Image.open(path)
        return ImageAsset(img)
    elif ext == '.xtc':
        return XTContainerAsset(path)
    elif ext in ['.xth', '.xtg']:
        return FileXTFrameAsset(path)
    else:
        logger.warning(f"Unknown file type: {path}")
        return None


@click.command(help="Convert files to XTC/XTH/XTG format.")
@click.argument("sources", type=click.Path(exists=True), nargs=-1, required=True)
@click.option("-o", "--output", type=click.Path(), required=True, help="Output file")
@click.option("-c", "--config", type=click.Path(exists=True), default=None, help="Config file")
def convert(sources: tuple[str, ...], output: str, config: Optional[str]):
    """Convert files to XTC/XTH/XTG format, or PNG/PDF for debugging.

    Examples:
        xtctool convert page1.png page2.jpg -o output.xtc
        xtctool convert document.pdf -o output.xtc
        xtctool convert input.pdf -o output.xth -c config.toml
        xtctool convert input.pdf -o debug.png  # Decode frames to PNG (debugging)
        xtctool convert input.pdf -o debug.pdf  # Decode frames to PDF (debugging)
    """
    cfg = load_config(config)

    # Determine output mode
    output_path = Path(output)
    output_ext = output_path.suffix.lower()

    if output_ext not in ['.xtc', '.xth', '.xtg', '.png', '.pdf']:
        raise click.BadParameter(f"Output must be .xtc, .xth, .xtg, .png, or .pdf")

    if output_ext == '.xtc':
        output_mode = 'xtc'
    elif output_ext in ['.png', '.pdf']:
        output_mode = 'debug'  # Decode frames to images for debugging
    else:
        output_mode = 'single_pages'

    logger.info(f"Converting {len(sources)} source(s) -> {output} ({output_mode})")

    # Initialize stack (reversed for LIFO processing)
    stack = deque()
    for source in reversed(sources):
        asset = create_asset(source)
        if asset:
            stack.append(asset)

    # Process stack - always convert to frames
    frames = []
    processed_count = 0

    # Use tqdm to show progress (disable=None means auto-detect TTY)
    with tqdm(desc="Processing", unit=" frame", disable=None) as pbar:
        while stack:
            asset = stack.pop()
            asset_name = asset.__class__.__name__

            # Show what we're processing
            if hasattr(asset, 'path'):
                pbar.set_postfix_str(f"{asset_name}: {Path(asset.path).name}")
            else:
                pbar.set_postfix_str(f"{asset_name}")

            logger.debug(f"Processing: {asset_name}")

            # Convert asset
            result = asset.convert(cfg)

            # Handle result
            if isinstance(result, list):
                # Multiple assets (e.g., PDF → images, XTC → frames)
                # Reverse for LIFO stack so they come out in correct order
                stack.extend(reversed(result))
                tqdm.write(f"  -> {asset_name} produced {len(result)} items")
            elif isinstance(result, XTFrameAsset):
                # Final frame
                frames.append(result)
                # tqdm.write(f"  -> Generated {result.format.upper()} frame")
            elif result != asset:
                # Single converted asset
                stack.append(result)
            # If result == asset, it's final format, add to frames
            elif isinstance(asset, XTFrameAsset):
                frames.append(asset)
                tqdm.write(f"  -> Loaded {asset.format.upper()} frame")

            processed_count += 1
            pbar.update(1)
            pbar.set_description("Processing")

    logger.info(f"Processing complete: {len(frames)} frame(s)")

    # Write output based on mode
    if output_mode == 'xtc':
        write_xtc(output, frames, cfg)
    elif output_mode == 'debug':
        # Decode frames to images for debugging
        if output_ext == '.pdf':
            debug_output.write_pdf(output, frames, cfg)
        else:  # .png
            debug_output.write_png(output, frames, cfg)
    else:
        write_single_pages(output, frames)

    logger.info(f"Done: {output}")


def write_xtc(output: str, frames: list[XTFrameAsset], cfg: dict[str, Any]) -> None:
    """Write frames as XTC file."""
    from ..core.xtc import XTCWriter, XTCMetadata
    import time

    if not frames:
        logger.warning("No frames to write")
        return

    # Check all frames are same format
    formats = set(f.format for f in frames)
    if len(formats) > 1:
        raise ValueError(f"Mixed frame formats: {formats}. All frames must be same format.")

    page_format = frames[0].format
    logger.info(f"Writing XTC: {len(frames)} {page_format.upper()} pages -> {output}")

    # Get configuration
    output_cfg = cfg.get('output', {})
    width = output_cfg.get('width', 480)
    height = output_cfg.get('height', 800)

    # Create metadata
    metadata = XTCMetadata(
        title=output_cfg.get('title', ''),
        author=output_cfg.get('author', ''),
        publisher=output_cfg.get('publisher', ''),
        language=output_cfg.get('language', 'en-US'),
        create_time=int(time.time())
    )

    # Reading direction
    direction_map = {'ltr': 0, 'rtl': 1, 'ttb': 2}
    reading_direction = direction_map.get(output_cfg.get('direction', 'ltr'), 0)

    # Create XTC writer and write frames
    writer = XTCWriter(
        width=width,
        height=height,
        reading_direction=reading_direction,
        metadata=metadata,
        page_format=page_format
    )

    # Extract frame data and write
    frame_data_list = [frame.data for frame in frames]
    writer.write(output, frame_data_list)

    logger.info(f"Done: {output}")


def write_single_pages(output: str, frames: list[XTFrameAsset]) -> None:
    """Write frames as individual page files."""
    if not frames:
        logger.warning("No frames to write")
        return

    output_path = Path(output)
    stem = output_path.stem
    suffix = output_path.suffix
    parent = output_path.parent

    if len(frames) == 1:
        # Single frame - write directly
        with open(output, 'wb') as f:
            f.write(frames[0].data)
        logger.info(f"Wrote: {output}")
    else:
        # Multiple frames - write numbered files
        for idx, frame in enumerate(frames, 1):
            out_file = parent / f"{stem}_{idx:03d}{suffix}"
            with open(out_file, 'wb') as f:
                f.write(frame.data)
            logger.debug(f"Wrote: {out_file}")
        logger.info(f"Wrote {len(frames)} pages to {parent / stem}_*.{suffix}")


