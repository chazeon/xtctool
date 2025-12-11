"""Page selection utilities for multi-page documents."""

from typing import Optional


def parse_page_spec(path: str) -> tuple[str, Optional[str]]:
    """Parse page specification from path.

    Supports syntax: file.pdf:1-4, file.md:2, file.xtc:1,3,5

    Args:
        path: File path with optional page spec (e.g., "file.pdf:1-4")

    Returns:
        Tuple of (file_path, page_spec) where page_spec is None if not specified

    Examples:
        >>> parse_page_spec("file.pdf:1-4")
        ('file.pdf', '1-4')
        >>> parse_page_spec("file.pdf")
        ('file.pdf', None)
        >>> parse_page_spec("/path/to/file.md:2")
        ('/path/to/file.md', '2')
    """
    # Don't parse URLs
    if path.startswith(('http://', 'https://', 'ftp://')):
        return path, None

    # Check for page spec (colon followed by page specification)
    if ':' in path:
        # Split on last colon to handle Windows paths (C:\file.pdf)
        parts = path.rsplit(':', 1)
        # Valid page spec contains digits, commas, or dashes (e.g., "1-4", "-3", "1,3,5")
        if len(parts) == 2 and parts[1] and any(c.isdigit() for c in parts[1]):
            return parts[0], parts[1]

    return path, None


def parse_page_range(spec: str, total_pages: int) -> list[int]:
    """Parse page range specification into list of page numbers.

    Inspired by: https://rosettacode.org/wiki/Range_expansion

    Supports:
    - Single page: "5"
    - Range: "1-4" (pages 1,2,3,4)
    - Multiple: "1,3,5" (pages 1,3,5)
    - Complex: "1-4,7,10-12" (pages 1,2,3,4,7,10,11,12)
    - Open-ended: "5-" (page 5 to end), "-3" (first 3 pages)

    Args:
        spec: Page specification string
        total_pages: Total number of pages available

    Returns:
        List of page numbers in order, duplicates removed (1-indexed)

    Examples:
        >>> parse_page_range("1-4", 10)
        [1, 2, 3, 4]
        >>> parse_page_range("1,3,5", 10)
        [1, 3, 5]
        >>> parse_page_range("1-4,7,10-12", 15)
        [1, 2, 3, 4, 7, 10, 11, 12]
        >>> parse_page_range("5-", 10)
        [5, 6, 7, 8, 9, 10]
        >>> parse_page_range("-3", 10)
        [1, 2, 3]
    """
    pages = []

    for part in spec.split(','):
        part = part.strip()

        # Special case: "-3" means "first 3 pages"
        if part.startswith('-') and len(part) > 1:
            end = int(part[1:])
            pages.extend(range(1, end + 1))

        # Range: "1-4" or "5-" (check for '-' after first character)
        elif '-' in part[1:]:
            # Split on first dash after first character
            left, right = part[1:].split('-', 1)
            left = part[0] + left  # Reconstruct left side

            start = int(left)
            end = int(right) if right else total_pages
            pages.extend(range(start, end + 1))

        # Single page
        else:
            pages.append(int(part))

    # Remove duplicates and out-of-range pages, preserving order
    seen = set()
    valid_pages = []
    for p in pages:
        if 1 <= p <= total_pages and p not in seen:
            valid_pages.append(p)
            seen.add(p)

    return valid_pages
