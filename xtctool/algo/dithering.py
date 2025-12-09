"""Floyd-Steinberg dithering algorithms with optional numba acceleration."""

import numpy as np
from typing import Tuple, Union

# Try to import numba for JIT compilation
try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    # Dummy decorator if numba not available
    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        def decorator(func):
            return func
        return decorator


@njit(cache=True)
def _floyd_steinberg_core_2level(
    gray_array: np.ndarray,
    threshold: float,
    dither_strength: float
) -> np.ndarray:
    """Core Floyd-Steinberg for 2-level (binary) quantization.

    Args:
        gray_array: Input grayscale array (float32)
        threshold: Threshold value for binarization
        dither_strength: Error diffusion strength (0.0-1.0)

    Returns:
        Binary array with values 0-1
    """
    height, width = gray_array.shape
    working = gray_array.copy()
    result = np.zeros((height, width), dtype=np.uint8)

    # Error distribution weights
    w_right = (7/16) * dither_strength
    w_bl = (3/16) * dither_strength
    w_b = (5/16) * dither_strength
    w_br = (1/16) * dither_strength

    for y in range(height):
        for x in range(width):
            old_val = working[y, x]

            # Binary quantization
            if old_val < threshold:
                level = 0
                new_val = 0.0
            else:
                level = 1
                new_val = 255.0

            result[y, x] = level
            error = old_val - new_val

            # Distribute error to neighbors
            if x + 1 < width:
                working[y, x + 1] += error * w_right
            if y + 1 < height:
                if x > 0:
                    working[y + 1, x - 1] += error * w_bl
                working[y + 1, x] += error * w_b
                if x + 1 < width:
                    working[y + 1, x + 1] += error * w_br

    return result


@njit(cache=True)
def _floyd_steinberg_core_4level(
    gray_array: np.ndarray,
    threshold1: float,
    threshold2: float,
    threshold3: float,
    dither_strength: float
) -> np.ndarray:
    """Core Floyd-Steinberg for 4-level grayscale quantization.

    Args:
        gray_array: Input grayscale array (float32)
        threshold1: First threshold (e.g., 85)
        threshold2: Second threshold (e.g., 170)
        threshold3: Third threshold (e.g., 255)
        dither_strength: Error diffusion strength (0.0-1.0)

    Returns:
        4-level array with values 0-3
    """
    height, width = gray_array.shape
    working = gray_array.copy()
    result = np.zeros((height, width), dtype=np.uint8)

    # Error distribution weights
    w_right = (7/16) * dither_strength
    w_bl = (3/16) * dither_strength
    w_b = (5/16) * dither_strength
    w_br = (1/16) * dither_strength

    for y in range(height):
        for x in range(width):
            old_val = working[y, x]

            # 4-level quantization
            if old_val < threshold1:
                level = 0
                new_val = 0.0
            elif old_val < threshold2:
                level = 1
                new_val = 85.0
            elif old_val < threshold3:
                level = 2
                new_val = 170.0
            else:
                level = 3
                new_val = 255.0

            result[y, x] = level
            error = old_val - new_val

            # Distribute error to neighbors
            if x + 1 < width:
                working[y, x + 1] += error * w_right
            if y + 1 < height:
                if x > 0:
                    working[y + 1, x - 1] += error * w_bl
                working[y + 1, x] += error * w_b
                if x + 1 < width:
                    working[y + 1, x + 1] += error * w_br

    return result


def floyd_steinberg_dither(
    gray_array: np.ndarray,
    levels: Union[int, Tuple[float, ...]],
    dither_strength: float = 0.8
) -> np.ndarray:
    """Apply Floyd-Steinberg dithering to grayscale image.

    Args:
        gray_array: Input grayscale array (uint8 or float32)
        levels: Either:
            - int 2: Binary (threshold at 128)
            - int 4: 4-level (thresholds at 85, 170, 255)
            - tuple of thresholds for custom levels
        dither_strength: Error diffusion strength (0.0-1.0)

    Returns:
        Quantized array with level indices

    Example:
        # Binary (2-level)
        result = floyd_steinberg_dither(image, 2)

        # 4-level with default thresholds
        result = floyd_steinberg_dither(image, 4)

        # 4-level with custom thresholds
        result = floyd_steinberg_dither(image, (85, 170, 255))

        # Binary with custom threshold
        result = floyd_steinberg_dither(image, (128,))
    """
    # Convert to float32 for processing
    if gray_array.dtype != np.float32:
        working = gray_array.astype(np.float32)
    else:
        working = gray_array

    # Determine quantization mode
    if isinstance(levels, int):
        if levels == 2:
            # Binary with default threshold
            return _floyd_steinberg_core_2level(working, 128.0, dither_strength)
        elif levels == 4:
            # 4-level with default thresholds
            return _floyd_steinberg_core_4level(working, 85.0, 170.0, 255.0, dither_strength)
        else:
            raise ValueError(f"Unsupported level count: {levels}. Use 2 or 4, or provide thresholds.")

    elif isinstance(levels, (tuple, list)):
        if len(levels) == 1:
            # Binary with custom threshold
            return _floyd_steinberg_core_2level(working, float(levels[0]), dither_strength)
        elif len(levels) == 3:
            # 4-level with custom thresholds
            return _floyd_steinberg_core_4level(
                working,
                float(levels[0]),
                float(levels[1]),
                float(levels[2]),
                dither_strength
            )
        else:
            raise ValueError(f"Unsupported threshold count: {len(levels)}. Use 1 or 3 thresholds.")

    else:
        raise TypeError(f"levels must be int or tuple, got {type(levels)}")
