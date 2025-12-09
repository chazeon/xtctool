"""Test the conversion pipeline: Image -> Frame -> Image."""

import pytest
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

from xtctool.assets import ImageAsset
from xtctool.debug.output import decode_frame_to_image


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        'output': {
            'width': 480,
            'height': 800,
        },
        'xth': {
            'threshold1': 85,
            'threshold2': 170,
            'threshold3': 255,
            'invert': False,
            'dither': True,
            'dither_strength': 0.8,
        }
    }


@pytest.fixture
def test_image():
    """Create a test image with patterns."""
    width, height = 480, 800
    img = Image.new('L', (width, height), 255)
    draw = ImageDraw.Draw(img)

    # Gradient
    for y in range(0, height // 3):
        gray = int(255 * y / (height // 3))
        draw.line([(0, y), (width, y)], fill=gray)

    # Rectangles with different gray levels
    draw.rectangle([50, height // 3 + 50, 150, height // 3 + 150], fill=0)
    draw.rectangle([200, height // 3 + 50, 300, height // 3 + 150], fill=85)
    draw.rectangle([350, height // 3 + 50, 450, height // 3 + 150], fill=170)

    # Random noise
    noise = np.random.randint(0, 256, (height // 6, width), dtype=np.uint8)
    noise_img = Image.fromarray(noise, mode='L')
    img.paste(noise_img, (0, 5 * height // 6))

    return img


def test_image_asset_creation(test_image):
    """Test ImageAsset can be created from PIL Image."""
    asset = ImageAsset(test_image)
    assert asset.image == test_image
    assert asset.image.size == (480, 800)
    assert asset.image.mode == 'L'


def test_image_to_frame_conversion(test_image, test_config):
    """Test ImageAsset converts to FrameAsset."""
    img_asset = ImageAsset(test_image)
    frame_asset = img_asset.convert(test_config)

    assert frame_asset.format == 'xth'
    assert len(frame_asset.data) > 0
    assert isinstance(frame_asset.data, bytes)


def test_frame_decode(test_image, test_config):
    """Test FrameAsset can be decoded back to image."""
    img_asset = ImageAsset(test_image)
    frame_asset = img_asset.convert(test_config)
    decoded_img = decode_frame_to_image(frame_asset)

    assert decoded_img.size == test_image.size
    assert decoded_img.mode == 'L'


def test_roundtrip_pipeline(test_image, test_config, tmp_path):
    """Test complete Image -> Frame -> Image roundtrip."""
    # Convert to frame
    img_asset = ImageAsset(test_image)
    frame_asset = img_asset.convert(test_config)

    # Decode back
    decoded_img = decode_frame_to_image(frame_asset)

    # Verify dimensions
    assert decoded_img.size == test_image.size, "Size should match"
    assert decoded_img.mode == test_image.mode, "Mode should match"

    # Verify data integrity (account for 4-level quantization)
    orig_array = np.array(test_image)
    dec_array = np.array(decoded_img)

    # Check decoded image only contains valid 4-level values
    unique_values = np.unique(dec_array)
    valid_levels = {0, 85, 170, 255}
    assert all(v in valid_levels for v in unique_values), \
        "Decoded image should only contain 4-level grayscale values"

    # Save for manual inspection
    test_image.save(tmp_path / "original.png")
    decoded_img.save(tmp_path / "decoded.png")


def test_frame_size_reasonable(test_image, test_config):
    """Test that frame size is reasonable (compressed)."""
    img_asset = ImageAsset(test_image)
    frame_asset = img_asset.convert(test_config)

    # XTH uses 2 bits per pixel, so should be ~1/4 the size of grayscale
    # Plus header overhead
    expected_data_size = (480 * 800 * 2) // 8 + 22  # 2 bits per pixel + header
    actual_size = len(frame_asset.data)

    assert actual_size > expected_data_size * 0.9, "Frame too small"
    assert actual_size < expected_data_size * 1.1, "Frame too large"
