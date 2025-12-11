#!/usr/bin/env python3
"""Create device mockup by compositing rendered page onto device image."""

import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw


def add_rounded_corners(image: Image.Image, radius: int) -> Image.Image:
    """Add rounded corners to an image.

    Args:
        image: Input image
        radius: Corner radius in pixels

    Returns:
        Image with rounded corners
    """
    # Create a mask with rounded corners
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)

    # Apply mask to image
    output = Image.new('RGBA', image.size, (0, 0, 0, 0))
    output.paste(image, (0, 0))
    output.putalpha(mask)

    return output


def create_mockup(device_path: str, page_path: str, output_path: str, opacity: float = 0.8):
    """Create mockup by pasting page onto device with multiply blend.

    Args:
        device_path: Path to device.png
        page_path: Path to rendered page (e.g., pg1661-images-3.png)
        output_path: Path to save mockup
        opacity: Opacity for the page layer (0.0-1.0), default 0.8
    """
    # Open images
    device = Image.open(device_path).convert('RGBA')
    page = Image.open(page_path).convert('RGBA')

    # Add 2px rounded corners to page
    page = add_rounded_corners(page, radius=6)

    # Calculate center position
    device_w, device_h = device.size
    page_w, page_h = page.size
    x = (device_w - page_w) // 2 - 4
    y = (device_h - page_h) // 2 - 61

    # Create a new image for the page with opacity
    page_with_opacity = Image.new('RGBA', device.size, (255, 255, 255, 0))
    page_with_opacity.paste(page, (x, y))

    # Apply opacity
    alpha = page_with_opacity.split()[3]
    alpha = alpha.point(lambda p: int(p * opacity))
    page_with_opacity.putalpha(alpha)

    # Convert to RGB for multiply blend
    device_rgb = device.convert('RGB')
    page_rgb = page_with_opacity.convert('RGB')

    # Multiply blend mode
    multiplied = ImageChops.multiply(device_rgb, page_rgb)

    # Paste multiplied result using alpha mask
    result = device.copy()
    result.paste(multiplied, (0, 0), page_with_opacity.split()[3])

    # Save
    result.save(output_path)
    print(f"Mockup saved to: {output_path}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python mockup.py <page.png> <output.png>")
        print("Example: python mockup.py pg1661-images-3.png mockup.png")
        sys.exit(1)

    page_path = sys.argv[1]
    output_path = sys.argv[2]
    device_path = "device.png"

    if not Path(device_path).exists():
        print(f"Error: {device_path} not found")
        sys.exit(1)

    if not Path(page_path).exists():
        print(f"Error: {page_path} not found")
        sys.exit(1)

    create_mockup(device_path, page_path, output_path)
