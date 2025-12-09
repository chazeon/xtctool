"""XTH format - 4-level grayscale image format for e-paper displays."""

import struct
from typing import Tuple
import numpy as np
from PIL import Image

from ..algo.dithering import floyd_steinberg_dither


class XTHWriter:
    """Writer for XTH format files (4-level grayscale)."""

    MAGIC = 0x00485458  # "XTH\0" in little-endian
    HEADER_SIZE = 22

    def __init__(self, width: int, height: int):
        """Initialize XTH writer.

        Args:
            width: Image width in pixels
            height: Image height in pixels
        """
        self.width = width
        self.height = height

    def _convert_to_4level(
        self,
        image: Image.Image,
        thresholds: Tuple[int, int, int] = (85, 170, 255),
        invert: bool = False,
        enable_dithering: bool = True,
        dither_strength: float = 0.8
    ) -> np.ndarray:
        """Convert image to 4-level grayscale using threshold-based quantization.

        Args:
            image: Input PIL Image
            thresholds: Three threshold values for 4-level conversion (default: 85, 170, 255)
            invert: Invert colors (applies to source image before quantization)
            enable_dithering: Enable Floyd-Steinberg dithering
            dither_strength: Dithering strength (0.0-1.0)

        Returns:
            2D numpy array with values 0-3
        """
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')

        # Resize to target dimensions if needed
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)

        # Apply invert to source if requested
        if invert:
            image = Image.eval(image, lambda x: 255 - x)

        # Convert to numpy array
        gray_array = np.array(image, dtype=np.uint8)

        if enable_dithering:
            # Use optimized Floyd-Steinberg from algo module (numba-accelerated if available)
            result = floyd_steinberg_dither(gray_array, thresholds, dither_strength)
        else:
            # Simple threshold-based quantization without dithering
            gray_array = np.array(image, dtype=np.uint8)
            t1, t2, t3 = thresholds

            result = np.zeros((self.height, self.width), dtype=np.uint8)
            result[gray_array < t1] = 0
            result[(gray_array >= t1) & (gray_array < t2)] = 1
            result[(gray_array >= t2) & (gray_array < t3)] = 2
            result[gray_array >= t3] = 3

        return result

    def _encode_bitplanes(self, pixel_values: np.ndarray) -> Tuple[bytearray, bytearray]:
        """Encode pixel values into two bit planes using vertical scan order.

        The XTH format uses a specific storage pattern:
        - Vertical scan order (column-major)
        - Columns scanned from RIGHT to LEFT (x = width-1 down to 0)
        - 8 vertical pixels packed per byte
        - MSB (bit 7) = topmost pixel in each group of 8

        Args:
            pixel_values: 2D array of pixel values (0-3)

        Returns:
            Tuple of (plane1_data, plane2_data) as bytearrays
        """
        # Map pixel values to match Xteink LUT (swapped middle values)
        # 0 -> 0 (white), 1 -> 2 (dark grey), 2 -> 1 (light grey), 3 -> 3 (black)
        lut_map = {0: 0, 1: 2, 2: 1, 3: 3}
        mapped_values = np.vectorize(lambda x: lut_map[x])(pixel_values)

        # Invert to match display behavior
        mapped_values = 3 - mapped_values

        plane1 = bytearray()
        plane2 = bytearray()

        # Scan columns from right to left
        for x in range(self.width - 1, -1, -1):
            # Process column in groups of 8 vertical pixels
            for y in range(0, self.height, 8):
                byte1 = 0
                byte2 = 0

                # Pack 8 vertical pixels
                for i in range(8):
                    if y + i < self.height:
                        pixel_val = mapped_values[y + i, x]
                        bit1 = (pixel_val >> 1) & 1  # High bit
                        bit2 = pixel_val & 1          # Low bit

                        # MSB = topmost pixel
                        byte1 |= bit1 << (7 - i)
                        byte2 |= bit2 << (7 - i)

                plane1.append(byte1)
                plane2.append(byte2)

        return plane1, plane2

    def encode(
        self,
        image: Image.Image,
        thresholds: Tuple[int, int, int] = (85, 170, 255),
        invert: bool = False,
        enable_dithering: bool = True,
        dither_strength: float = 0.8
    ) -> bytes:
        """Encode image to XTH format as bytes.

        Args:
            image: Input PIL Image
            thresholds: Three threshold values for 4-level conversion
            invert: Invert colors
            enable_dithering: Enable Floyd-Steinberg dithering
            dither_strength: Dithering strength (0.0-1.0)

        Returns:
            Complete XTH file data as bytes
        """
        # Convert to 4-level grayscale
        pixel_values = self._convert_to_4level(
            image, thresholds, invert, enable_dithering, dither_strength
        )

        # Encode to bit planes
        plane1, plane2 = self._encode_bitplanes(pixel_values)

        # Calculate data size
        data_size = len(plane1) + len(plane2)

        # Calculate simple checksum (sum of all bytes)
        checksum = sum(plane1) + sum(plane2)

        # Build complete file data
        data = bytearray()
        data.extend(struct.pack('<I', self.MAGIC))           # magic (4 bytes)
        data.extend(struct.pack('<H', self.width))           # width (2 bytes)
        data.extend(struct.pack('<H', self.height))          # height (2 bytes)
        data.extend(struct.pack('<B', 0))                    # colorMode (1 byte)
        data.extend(struct.pack('<B', 0))                    # compression (1 byte)
        data.extend(struct.pack('<I', data_size))            # dataSize (4 bytes)
        data.extend(struct.pack('<Q', checksum & 0xFFFFFFFFFFFFFFFF))  # md5/checksum (8 bytes)
        data.extend(plane1)
        data.extend(plane2)

        return bytes(data)

    def write(
        self,
        output_path: str,
        image: Image.Image,
        thresholds: Tuple[int, int, int] = (85, 170, 255),
        invert: bool = False,
        enable_dithering: bool = True,
        dither_strength: float = 0.8
    ) -> None:
        """Write image to XTH file.

        Args:
            output_path: Output file path
            image: Input PIL Image
            thresholds: Three threshold values for 4-level conversion
            invert: Invert colors
            enable_dithering: Enable Floyd-Steinberg dithering
            dither_strength: Dithering strength (0.0-1.0)
        """
        data = self.encode(image, thresholds, invert, enable_dithering, dither_strength)
        with open(output_path, 'wb') as f:
            f.write(data)


class XTHReader:
    """Reader for XTH format files (4-level grayscale)."""

    MAGIC = 0x00485458  # "XTH\0" in little-endian
    HEADER_SIZE = 22

    def decode(self, data: bytes) -> Image.Image:
        """Decode XTH format bytes to PIL Image.

        Args:
            data: Complete XTH file data (with header)

        Returns:
            PIL Image in grayscale mode
        """
        # Parse header
        magic = struct.unpack('<I', data[0:4])[0]
        if magic != self.MAGIC:
            raise ValueError(f"Invalid XTH magic: {magic:#x}, expected {self.MAGIC:#x}")

        width = struct.unpack('<H', data[4:6])[0]
        height = struct.unpack('<H', data[6:8])[0]

        # Extract bit planes
        bitplane_data = data[self.HEADER_SIZE:]
        bitplane_size = len(bitplane_data) // 2
        plane1 = bitplane_data[:bitplane_size]
        plane2 = bitplane_data[bitplane_size:]

        # Decode bit planes to pixel values
        pixels = np.zeros((height, width), dtype=np.uint8)

        # Decode vertical scan order (right to left columns)
        bit_idx = 0
        for x in range(width - 1, -1, -1):
            for y in range(0, height, 8):
                byte_idx = bit_idx // 8
                byte1 = plane1[byte_idx] if byte_idx < len(plane1) else 0
                byte2 = plane2[byte_idx] if byte_idx < len(plane2) else 0

                for i in range(8):
                    if y + i < height:
                        bit1 = (byte1 >> (7 - i)) & 1
                        bit2 = (byte2 >> (7 - i)) & 1
                        val = (bit1 << 1) | bit2

                        # Reverse the encoding transformations
                        val = 3 - val  # Reverse inversion
                        lut_reverse = {0: 0, 2: 1, 1: 2, 3: 3}  # Reverse LUT mapping
                        pixels[y + i, x] = lut_reverse.get(val, val) * 85  # Map to 0, 85, 170, 255

                bit_idx += 8

        return Image.fromarray(pixels, mode='L')

    def read(self, file_path: str) -> Image.Image:
        """Read and decode XTH file to PIL Image.

        Args:
            file_path: Path to XTH file

        Returns:
            PIL Image in grayscale mode
        """
        with open(file_path, 'rb') as f:
            data = f.read()
        return self.decode(data)
