# xtctool

Convert images and documents to XTH/XTG/XTC formats for ESP32 e-paper displays.

## Features

- **Unified conversion pipeline** - handles multiple input formats through a single `convert` command
- **Multiple input formats**: PDF, PNG, JPEG, XTC, XTH, XTG
- **Multiple output formats**:
  - **XTH** - 4-level grayscale (2 bits per pixel)
  - **XTG** - 1-bit monochrome (1 bit per pixel)
  - **XTC** - multi-page container with metadata
- **Configuration via TOML** - easily manage conversion settings
- **Floyd-Steinberg dithering** - optional high-quality dithering with configurable strength
- **Debug output** - decode frames back to PNG/PDF for inspection
- **Direct upload** - send files directly to ESP32 devices over HTTP

## Installation

### Using uv (recommended)

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install xtctool
uv pip install -e .

# Or with optional dependencies
uv pip install -e ".[performance]"  # Adds numba for ~10x faster dithering
```

### Using pip

```bash
# Basic installation
pip install .

# With development tools
pip install -e ".[dev]"

# With performance optimization
pip install ".[performance]"
```

### Dependencies

All required dependencies are automatically installed:
- **PyMuPDF** (fitz) - PDF rendering (no external tools needed!)
- **Pillow** - Image processing
- **NumPy** - Array operations
- **Click** - CLI interface
- **tqdm** - Progress bars

Optional:
- **numba** - JIT compilation for 10x faster dithering (install with `[performance]` extra)

## Quick Start

### Basic conversion

```bash
# Convert PDF to XTH (4-level grayscale)
uv run xtctool convert input.pdf -o output.xth

# Convert images to XTC container
uv run xtctool convert page1.png page2.jpg page3.png -o output.xtc

# Convert entire PDF to multi-page XTC
uv run xtctool convert document.pdf -o document.xtc
```

### With configuration file

```bash
# Create config from example
cp config.toml.example config.toml

# Edit config.toml with your settings
# Then convert using config
uv run xtctool convert input.pdf -o output.xtc -c config.toml
```

### Upload to device

```bash
# Upload to ESP32 e-paper display
uv run xtctool upload output.xtc --host 192.168.1.100
```

## Usage

### Convert Command

The `convert` command handles all format conversions through a unified pipeline:

```bash
xtctool convert [OPTIONS] SOURCES... -o OUTPUT
```

**Arguments:**
- `SOURCES`: One or more input files (PDF, PNG, JPG, XTC, XTH, XTG)
- `-o, --output`: Output file path (required)
- `-c, --config`: Optional configuration file (TOML format)

**Output format** is determined by the file extension:
- `.xth` - Single 4-level grayscale page (or multiple numbered files)
- `.xtg` - Single 1-bit monochrome page (or multiple numbered files)
- `.xtc` - Multi-page container with metadata
- `.png` - Debug output (decoded frames)
- `.pdf` - Debug output (multi-page decoded frames)

### Examples

**Convert PDF to 4-level grayscale pages:**
```bash
# Single page PDF → single XTH file
xtctool convert page.pdf -o output.xth

# Multi-page PDF → numbered XTH files (output_001.xth, output_002.xth, ...)
xtctool convert document.pdf -o output.xth
```

**Convert PDF to XTC container:**
```bash
# All pages in one container with metadata
xtctool convert manga.pdf -o manga.xtc -c config.toml
```

**Convert images to XTC:**
```bash
# Multiple images → XTC container
xtctool convert page1.png page2.jpg page3.png -o comic.xtc
```

**Convert to 1-bit monochrome (XTG):**
```bash
# Use XTG for pure black and white
xtctool convert input.pdf -o output.xtg
```

**Decode frames for debugging:**
```bash
# Convert XTC back to PNG images for inspection
xtctool convert input.xtc -o debug.png

# Convert XTC back to multi-page PDF
xtctool convert input.xtc -o debug.pdf
```

**Mix different input formats:**
```bash
# Combine PDFs, images, and existing frames
xtctool convert cover.png chapter1.pdf chapter2.pdf -o book.xtc
```

### Upload Command

Upload files directly to ESP32 e-paper devices:

```bash
xtctool upload FILE --host HOST [OPTIONS]
```

**Options:**
- `--host, -h`: Device IP address (required)
- `--port, -p`: Device port (default: 80)
- `--remote-path, -r`: Remote file path (default: same as local filename)

**Examples:**
```bash
# Basic upload
xtctool upload comic.xtc --host 192.168.1.100

# Upload to specific path
xtctool upload page.xth --host 192.168.1.100 --remote-path /comics/page1.xth

# Upload to different port
xtctool upload output.xtc --host 192.168.1.100 --port 8080
```

## Configuration

Create a `config.toml` file to manage conversion settings:

```toml
# config.toml

[output]
# Output dimensions
width = 480
height = 800

# XTC metadata (only used for .xtc output)
title = "My Comic"
author = "Author Name"
publisher = "Publisher Name"
language = "en-US"
direction = "ltr"  # ltr, rtl, or ttb

[pdf]
# PDF rendering resolution in DPI
resolution = 144

[xth]
# 4-level grayscale thresholds (0-255)
threshold1 = 85    # Below this: Black
threshold2 = 170   # T1-T2: Dark gray
threshold3 = 255   # T2-T3: Light gray, Above: White
invert = false
dither = true
dither_strength = 0.8

[xtg]
# 1-bit monochrome threshold (0-255)
threshold = 128
invert = false
dither = true
dither_strength = 0.8
```

Then use it with:
```bash
xtctool convert input.pdf -o output.xtc -c config.toml
```

### Configuration Options

**`[output]` section:**
- `width`, `height`: Target dimensions in pixels
- `title`, `author`, `publisher`, `language`: XTC metadata
- `direction`: Reading direction (`ltr`, `rtl`, `ttb`)

**`[pdf]` section:**
- `resolution`: PDF rendering DPI (higher = better quality, larger files)

**`[xth]` section (4-level grayscale):**
- `threshold1`, `threshold2`, `threshold3`: Grayscale quantization thresholds
- `invert`: Invert black/white
- `dither`: Enable Floyd-Steinberg dithering
- `dither_strength`: Dithering intensity (0.0-1.0)

**`[xtg]` section (1-bit monochrome):**
- `threshold`: Binarization threshold
- `invert`: Invert black/white
- `dither`: Enable Floyd-Steinberg dithering
- `dither_strength`: Dithering intensity (0.0-1.0)

## File Formats

### Input Formats

- **PDF** (`.pdf`) - Rendered page-by-page using PyMuPDF
- **Images** (`.png`, `.jpg`, `.jpeg`) - Standard image formats
- **XTC** (`.xtc`) - Multi-page container (can be decoded)
- **XTH** (`.xth`) - 4-level grayscale frame (can be reprocessed)
- **XTG** (`.xtg`) - 1-bit monochrome frame (can be reprocessed)

### Output Formats

#### XTH - 4-Level Grayscale

- 2 bits per pixel (4 grayscale levels: black, dark gray, light gray, white)
- Vertical bitplane encoding for efficient e-paper rendering
- Optimized for Xteink e-paper display LUT
- File size: `width × height × 2 bits + header`

#### XTG - 1-Bit Monochrome

- 1 bit per pixel (pure black and white)
- Row-major bitmap encoding
- Smallest file size for simple graphics
- File size: `width × height × 1 bit + header`

#### XTC - Container Format

- Stores multiple XTH or XTG pages
- Supports metadata (title, author, publisher, language)
- Configurable reading direction (LTR, RTL, TTB)
- Index table for fast page access
- File size: sum of all pages + metadata + index

## Advanced Usage

### Adjusting Grayscale Thresholds

For **XTH** (4-level grayscale), three thresholds define the levels:

```toml
[xth]
threshold1 = 85    # 0-85 → Black
threshold2 = 170   # 86-170 → Dark gray
threshold3 = 255   # 171-255 → Light gray
```

**Tips:**
- **Darker images**: Decrease all thresholds (`60, 140, 220`)
- **Lighter images**: Increase all thresholds (`100, 180, 255`)
- **High contrast**: Increase spacing (`50, 150, 250`)
- **Low contrast**: Decrease spacing (`100, 140, 180`)

### Dithering Options

Dithering improves perceived quality by distributing quantization errors:

```toml
[xth]
dither = true
dither_strength = 0.8  # 0.0 (off) to 1.0 (full)
```

**Strength guide:**
- `1.0` - Full dithering, best for photos
- `0.8` - Balanced (default)
- `0.5` - Subtle dithering
- `0.0` - No dithering (posterization)

**Performance:** Install `numba` for ~10x faster dithering:
```bash
pip install ".[performance]"
```

### Debug Output

Decode frames back to images for quality inspection:

```bash
# Decode single XTH/XTG to PNG
xtctool convert output.xth -o debug.png

# Decode XTC to multi-page PDF (lossless, high quality)
xtctool convert output.xtc -o debug.pdf

# Decode XTC to numbered PNGs
xtctool convert output.xtc -o debug.png  # Creates debug_001.png, debug_002.png, ...
```

Debug PDFs now use lossless compression (quality=100) to show true frame quality without JPEG artifacts.

## Development

### Running Tests

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=xtctool

# Run specific test file
uv run pytest tests/test_pdf_pipeline.py -v
```

### Code Quality

```bash
# Format code
black xtctool/

# Type checking
mypy xtctool/

# Lint
ruff check xtctool/
```

### Project Structure

```
xtctool/
├── assets/          # Conversion pipeline assets
│   ├── pdf.py       # PDF to images
│   ├── image.py     # Image processing
│   ├── xtframe.py   # XTH/XTG frames
│   └── xtcontainer.py  # XTC containers
├── core/            # Format encoders/decoders
│   ├── xth.py       # XTH format (4-level)
│   ├── xtg.py       # XTG format (1-bit)
│   └── xtc.py       # XTC container
├── utils/           # Utility modules
│   └── pdf.py       # PDF renderer (PyMuPDF)
├── algo/            # Algorithms
│   └── dithering.py # Floyd-Steinberg dithering
├── cli/             # Command-line interface
│   ├── convert.py   # Convert command
│   └── upload.py    # Upload command
└── debug/           # Debug utilities
    └── output.py    # Frame decoding
```

## Technical Details

### XTH Format Specification

- **Magic**: `0x00485458` ("XTH\0")
- **Encoding**: Two vertical bitplanes (column-major, right-to-left)
- **Pixel mapping** for Xteink e-paper:
  - `00` (0) → White
  - `01` (1) → Dark Gray
  - `10` (2) → Light Gray
  - `11` (3) → Black

### XTG Format Specification

- **Magic**: `0x00475458` ("XTG\0")
- **Encoding**: Row-major bitmap (1 bit per pixel)
- **Pixel mapping**: `0` = White, `1` = Black

### XTC Container Specification

- **Magic**: `0x00435458` ("XTC\0")
- **Structure**: Header → Metadata → Page Index → Pages
- **Supports**: Multiple pages, metadata, reading direction

See `XTC-XTG-XTH-XTCH.md` for detailed format specifications, or refer to the [XTC/XTH format specification][format-spec] for additional technical details.

## Troubleshooting

**Issue: Low quality output**
- Increase PDF resolution: `resolution = 200` in config
- Adjust dithering strength: `dither_strength = 0.9`
- Check debug output: `xtctool convert output.xtc -o debug.pdf`

**Issue: Slow conversion**
- Install numba for faster dithering: `pip install ".[performance]"`
- Lower PDF resolution: `resolution = 120`

**Issue: Images too dark/light**
- Adjust XTH thresholds in config.toml
- For dark images: decrease thresholds
- For light images: increase thresholds

**Issue: Wrong size/aspect ratio or cropping**
- **Manual resolution tuning required**: The PDF rendering resolution must be manually matched to your target display dimensions
- Calculate the appropriate DPI based on your PDF's page size to fit the target resolution (e.g., 480×800)
- For example: A Letter-size PDF (8.5"×11") at 144 DPI renders to ~1224×1584 pixels, which needs scaling to fit 480×800
- Adjust `resolution` in config.toml to achieve the desired output size
- Refer to the [format specification][format-spec] for display dimension requirements

**Issue: Upload fails**
- Check device IP: `ping 192.168.1.100`
- Verify device is running HTTP server
- Check firewall settings

## License

This project is licensed under the GNU GPLv3 License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

For bugs and feature requests, please open an issue on GitHub.

## Acknowledgments

- [XTC/XTG/XTH format specification][format-spec]
- Xteink e-paper display project
- PyMuPDF for efficient PDF rendering

[format-spec]: https://gist.github.com/CrazyCoder/b125f26d6987c0620058249f59f1327d
