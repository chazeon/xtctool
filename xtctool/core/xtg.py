"""XTG format - Monochrome 1-bit image format for e-paper displays."""

import struct
import numpy as np
from PIL import Image

from ..algo.dithering import floyd_steinberg_dither


class XTGWriter:
    """Writer for XTG format files (monochrome 1-bit)."""

    MAGIC = 0x00475458  # "XTG\0" in little-endian
    HEADER_SIZE = 22

    def __init__(self, width: int, height: int):
        """Initialize XTG writer.

        Args:
            width: Image width in pixels
            height: Image height in pixels
        """
        self.width = width
        self.height = height

    def _convert_to_monochrome(
        self,
        image: Image.Image,
        threshold: int = 128,
        invert: bool = False,
        enable_dithering: bool = True,
        dither_strength: float = 0.8
    ) -> np.ndarray:
        """Convert image to monochrome (1-bit).

        Args:
            image: Input PIL Image
            threshold: Threshold value for binarization (0-255)
            invert: Invert colors
            enable_dithering: Enable Floyd-Steinberg dithering
            dither_strength: Dithering strength (0.0-1.0)

        Returns:
            2D numpy array with values 0 or 1
        """
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')

        # Resize to target dimensions if needed
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)

        # Convert to numpy array
        gray_array = np.array(image, dtype=np.uint8)

        if enable_dithering:
            # Use optimized Floyd-Steinberg from algo module (numba-accelerated if available)
            result = floyd_steinberg_dither(gray_array, (threshold,), dither_strength)
        else:
            # Simple threshold-based quantization without dithering
            result = np.zeros((self.height, self.width), dtype=np.uint8)
            result[gray_array >= threshold] = 1

        # Invert if needed
        if invert:
            result = 1 - result

        return result

    def _encode_bitmap(self, pixel_values: np.ndarray) -> bytearray:
        """Encode pixel values into bitmap using row-major order.

        The XTG format uses:
        - Row-major storage (top to bottom, left to right)
        - 8 pixels per byte
        - MSB (bit 7) = leftmost pixel in each group of 8

        Args:
            pixel_values: 2D array of pixel values (0 or 1)

        Returns:
            Bitmap data as bytearray
        """
        bitmap_data = bytearray()
        bytes_per_row = (self.width + 7) // 8

        # Process row by row, top to bottom
        for y in range(self.height):
            # Process each byte in the row
            for byte_idx in range(bytes_per_row):
                byte_val = 0
                # Pack 8 pixels into one byte
                for bit_idx in range(8):
                    x = byte_idx * 8 + bit_idx
                    if x < self.width:
                        pixel = pixel_values[y, x]
                        # MSB = leftmost pixel
                        byte_val |= pixel << (7 - bit_idx)

                bitmap_data.append(byte_val)

        return bitmap_data

    def encode(
        self,
        image: Image.Image,
        threshold: int = 128,
        invert: bool = False,
        enable_dithering: bool = True,
        dither_strength: float = 0.8
    ) -> bytes:
        """Encode image to XTG format as bytes.

        Args:
            image: Input PIL Image
            threshold: Threshold value for binarization (0-255)
            invert: Invert colors
            enable_dithering: Enable Floyd-Steinberg dithering
            dither_strength: Dithering strength (0.0-1.0)

        Returns:
            Complete XTG file data as bytes
        """
        # Convert to monochrome
        pixel_values = self._convert_to_monochrome(
            image, threshold, invert, enable_dithering, dither_strength
        )

        # Encode to bitmap
        bitmap_data = self._encode_bitmap(pixel_values)

        # Calculate data size
        data_size = len(bitmap_data)

        # Calculate simple checksum (sum of all bytes)
        checksum = sum(bitmap_data)

        # Build complete file data
        data = bytearray()
        data.extend(struct.pack('<I', self.MAGIC))           # magic (4 bytes)
        data.extend(struct.pack('<H', self.width))           # width (2 bytes)
        data.extend(struct.pack('<H', self.height))          # height (2 bytes)
        data.extend(struct.pack('<B', 0))                    # colorMode (1 byte)
        data.extend(struct.pack('<B', 0))                    # compression (1 byte)
        data.extend(struct.pack('<I', data_size))            # dataSize (4 bytes)
        data.extend(struct.pack('<Q', checksum & 0xFFFFFFFFFFFFFFFF))  # md5/checksum (8 bytes)
        data.extend(bitmap_data)

        return bytes(data)

    def write(
        self,
        output_path: str,
        image: Image.Image,
        threshold: int = 128,
        invert: bool = False,
        enable_dithering: bool = True,
        dither_strength: float = 0.8
    ) -> None:
        """Write image to XTG file.

        Args:
            output_path: Output file path
            image: Input PIL Image
            threshold: Threshold value for binarization (0-255)
            invert: Invert colors
            enable_dithering: Enable Floyd-Steinberg dithering
            dither_strength: Dithering strength (0.0-1.0)
        """
        data = self.encode(image, threshold, invert, enable_dithering, dither_strength)
        with open(output_path, 'wb') as f:
            f.write(data)


class XTGReader:
    """Reader for XTG format files (monochrome 1-bit)."""

    MAGIC = 0x00475458  # "XTG\0" in little-endian
    HEADER_SIZE = 22

    def decode(self, data: bytes) -> Image.Image:
        """Decode XTG format bytes to PIL Image.

        Args:
            data: Complete XTG file data (with header)

        Returns:
            PIL Image in grayscale mode (values 0 or 255)
        """
        # Parse header
        magic = struct.unpack('<I', data[0:4])[0]
        if magic != self.MAGIC:
            raise ValueError(f"Invalid XTG magic: {magic:#x}, expected {self.MAGIC:#x}")

        width = struct.unpack('<H', data[4:6])[0]
        height = struct.unpack('<H', data[6:8])[0]

        # Extract bitmap data
        bitmap_data = data[self.HEADER_SIZE:]
        pixels = np.zeros((height, width), dtype=np.uint8)

        # Decode row-major bitmap
        bytes_per_row = (width + 7) // 8
        for y in range(height):
            for byte_idx in range(bytes_per_row):
                data_idx = y * bytes_per_row + byte_idx
                if data_idx < len(bitmap_data):
                    byte_val = bitmap_data[data_idx]
                    for bit_idx in range(8):
                        x = byte_idx * 8 + bit_idx
                        if x < width:
                            pixel = (byte_val >> (7 - bit_idx)) & 1
                            pixels[y, x] = pixel * 255  # Map to 0 or 255

        return Image.fromarray(pixels, mode='L')

    def read(self, file_path: str) -> Image.Image:
        """Read and decode XTG file to PIL Image.

        Args:
            file_path: Path to XTG file

        Returns:
            PIL Image in grayscale mode
        """
        with open(file_path, 'rb') as f:
            data = f.read()
        return self.decode(data)
