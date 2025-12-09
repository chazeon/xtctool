"""Test PDF ingestion and output pipeline."""

import pytest
from PIL import Image
import urllib.request

from xtctool.utils import PDFConverter
from xtctool.assets import PDFAsset, ImageAsset, XTFrameAsset


@pytest.fixture(scope="session")
def test_pdf_path(tmp_path_factory):
    """Download and cache a small public domain PDF for testing.

    Uses a simple 1-page PDF from PDF specification examples.
    """
    cache_dir = tmp_path_factory.mktemp("pdf_cache")
    pdf_path = cache_dir / "test_sample.pdf"

    if not pdf_path.exists():
        # Download a small public domain PDF (Simple PDF example, ~6KB)
        # This is from the PDF specification examples - a minimal single-page document
        url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

        try:
            print(f"\nDownloading test PDF from {url}")
            urllib.request.urlretrieve(url, pdf_path)
            print(f"Downloaded to {pdf_path} ({pdf_path.stat().st_size} bytes)")
        except Exception as e:
            pytest.skip(f"Could not download test PDF: {e}")

    return str(pdf_path)


@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        'output': {
            'width': 480,
            'height': 800,
        },
        'pdf': {
            'resolution': 144,
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


def test_pdf_converter_page_count(test_pdf_path):
    """Test PDFConverter can read page count."""
    converter = PDFConverter(resolution=144)
    page_count = converter.get_page_count(test_pdf_path)

    assert page_count > 0, "PDF should have at least one page"
    print(f"PDF has {page_count} pages")


def test_pdf_converter_render_page(test_pdf_path):
    """Test PDFConverter can render a page."""
    converter = PDFConverter(resolution=144)
    image = converter.render_page(test_pdf_path, page_num=1)

    assert isinstance(image, Image.Image), "Should return PIL Image"
    assert image.mode == 'RGB', "Should be RGB mode"
    assert image.size[0] > 0 and image.size[1] > 0, "Should have valid dimensions"
    print(f"Rendered page 1: {image.size}, mode: {image.mode}")


def test_pdf_asset_creation(test_pdf_path):
    """Test PDFAsset can be created."""
    asset = PDFAsset(test_pdf_path)
    assert asset.path == test_pdf_path
    print(f"Created PDFAsset from {test_pdf_path}")


def test_pdf_asset_convert_to_images(test_pdf_path, test_config):
    """Test PDFAsset converts to ImageAssets."""
    pdf_asset = PDFAsset(test_pdf_path)
    image_assets = pdf_asset.convert(test_config)

    assert isinstance(image_assets, list), "Should return list"
    assert len(image_assets) > 0, "Should have at least one image"
    assert all(isinstance(asset, ImageAsset) for asset in image_assets), "All should be ImageAssets"

    print(f"PDF converted to {len(image_assets)} ImageAssets")

    # Check first image
    first_image = image_assets[0].image
    assert isinstance(first_image, Image.Image), "Should contain PIL Image"
    print(f"First image: {first_image.size}, mode: {first_image.mode}")


def test_image_asset_convert_to_frame(test_pdf_path, test_config):
    """Test ImageAsset converts to XTFrameAsset."""
    # Get first page as image
    pdf_asset = PDFAsset(test_pdf_path)
    image_assets = pdf_asset.convert(test_config)

    # Convert first image to frame
    frame_asset = image_assets[0].convert(test_config)

    assert isinstance(frame_asset, XTFrameAsset), "Should return XTFrameAsset"
    assert frame_asset.format == 'xth', "Should be XTH format"
    assert len(frame_asset.data) > 0, "Should have frame data"
    print(f"ImageAsset converted to XTFrameAsset: {len(frame_asset.data)} bytes, format: {frame_asset.format}")


def test_full_pdf_to_frames_pipeline(test_pdf_path, test_config):
    """Test complete PDF → ImageAssets → XTFrameAssets pipeline."""
    # Step 1: PDF → ImageAssets
    pdf_asset = PDFAsset(test_pdf_path)
    image_assets = pdf_asset.convert(test_config)
    print(f"Step 1: PDF → {len(image_assets)} ImageAssets")

    # Step 2: ImageAssets → XTFrameAssets
    frames = []
    for i, img_asset in enumerate(image_assets):
        frame = img_asset.convert(test_config)
        frames.append(frame)
        if i == 0:  # Print first frame details
            print(f"Step 2: ImageAsset → XTFrameAsset ({len(frame.data)} bytes)")

    assert len(frames) == len(image_assets), "Should have same number of frames as images"
    assert all(isinstance(f, XTFrameAsset) for f in frames), "All should be XTFrameAssets"
    print(f"Complete pipeline: {len(frames)} frames generated")


def test_frame_decode_back_to_image(test_pdf_path, test_config):
    """Test XTFrameAsset can be decoded back to image."""
    from xtctool.debug.output import decode_frame_to_image

    # Get first frame
    pdf_asset = PDFAsset(test_pdf_path)
    image_assets = pdf_asset.convert(test_config)
    frame = image_assets[0].convert(test_config)

    # Decode back to image
    decoded_img = decode_frame_to_image(frame)

    assert isinstance(decoded_img, Image.Image), "Should return PIL Image"
    assert decoded_img.mode == 'L', "Should be grayscale"
    print(f"Frame decoded back to image: {decoded_img.size}, mode: {decoded_img.mode}")
