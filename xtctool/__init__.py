"""XTC Tool - Convert PDF files to XTG/XTH/XTC format for ESP32 e-paper displays."""

# Version is managed in pyproject.toml
try:
    from importlib.metadata import version
    __version__ = version("xtctool")
except Exception:
    __version__ = "unknown"
