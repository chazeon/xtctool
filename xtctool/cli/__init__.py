"""Command-line interface for xtctool.

Modular CLI structure with separate command modules for better organization.
"""

import click

# Import all command functions from submodules
from .upload import upload
from .convert import convert


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Convert PDF files to XTG/XTH/XTC format for ESP32 e-paper displays."""
    pass

# Upload command
main.add_command(upload)
main.add_command(convert)


# Export main for external use
__all__ = ['main']


if __name__ == '__main__':
    main()
