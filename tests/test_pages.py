"""Test page selection utilities."""

import pytest
from xtctool.utils import parse_page_spec, parse_page_range


class TestParsePageSpec:
    """Test parse_page_spec function."""

    def test_simple_path(self):
        """Test path without page spec."""
        path, spec = parse_page_spec("file.pdf")
        assert path == "file.pdf"
        assert spec is None

    def test_path_with_page_spec(self):
        """Test path with page spec."""
        path, spec = parse_page_spec("file.pdf:1-4")
        assert path == "file.pdf"
        assert spec == "1-4"

    def test_single_page(self):
        """Test single page specification."""
        path, spec = parse_page_spec("document.md:5")
        assert path == "document.md"
        assert spec == "5"

    def test_absolute_path(self):
        """Test absolute path with page spec."""
        path, spec = parse_page_spec("/path/to/file.pdf:1,3,5")
        assert path == "/path/to/file.pdf"
        assert spec == "1,3,5"

    def test_url_no_parse(self):
        """Test that URLs are not parsed."""
        url = "https://example.com/file.pdf"
        path, spec = parse_page_spec(url)
        assert path == url
        assert spec is None

    def test_windows_path(self):
        """Test Windows path (C:) is not parsed as page spec."""
        # C:\path\file.pdf should not parse C as page spec
        path, spec = parse_page_spec("C:\\path\\file.pdf")
        assert path == "C:\\path\\file.pdf"
        assert spec is None

    def test_colon_without_digits(self):
        """Test colon not followed by digits."""
        path, spec = parse_page_spec("file:name.pdf")
        assert path == "file:name.pdf"
        assert spec is None

    def test_open_ended_start_spec(self):
        """Test open-ended start page spec (-3)."""
        path, spec = parse_page_spec("file.pdf:-3")
        assert path == "file.pdf"
        assert spec == "-3"


class TestParsePageRange:
    """Test parse_page_range function."""

    def test_single_page(self):
        """Test single page selection."""
        pages = parse_page_range("5", 10)
        assert pages == [5]

    def test_simple_range(self):
        """Test simple range."""
        pages = parse_page_range("1-4", 10)
        assert pages == [1, 2, 3, 4]

    def test_multiple_single_pages(self):
        """Test multiple single pages."""
        pages = parse_page_range("1,3,5", 10)
        assert pages == [1, 3, 5]

    def test_complex_range(self):
        """Test complex range with multiple parts."""
        pages = parse_page_range("1-4,7,10-12", 15)
        assert pages == [1, 2, 3, 4, 7, 10, 11, 12]

    def test_open_ended_right(self):
        """Test open-ended range (5-)."""
        pages = parse_page_range("5-", 10)
        assert pages == [5, 6, 7, 8, 9, 10]

    def test_open_ended_left(self):
        """Test open-ended range at start (-3)."""
        pages = parse_page_range("-3", 10)
        assert pages == [1, 2, 3]

    def test_out_of_range_filtered(self):
        """Test that out-of-range pages are filtered."""
        pages = parse_page_range("8-12", 10)
        assert pages == [8, 9, 10]

    def test_duplicate_removal(self):
        """Test that duplicates are removed."""
        pages = parse_page_range("1-3,2-4", 10)
        assert pages == [1, 2, 3, 4]

    def test_preserves_order(self):
        """Test that order is preserved (not sorted)."""
        pages = parse_page_range("5,3,1,2,4", 10)
        assert pages == [5, 3, 1, 2, 4]

    def test_range_preserves_order(self):
        """Test that ranges maintain natural order."""
        pages = parse_page_range("10-12,1-3", 15)
        assert pages == [10, 11, 12, 1, 2, 3]

    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        pages = parse_page_range(" 1 - 3 , 5 , 7 - 9 ", 10)
        assert pages == [1, 2, 3, 5, 7, 8, 9]

    def test_single_page_out_of_range(self):
        """Test single page out of range is filtered."""
        pages = parse_page_range("15", 10)
        assert pages == []

    def test_all_out_of_range(self):
        """Test all pages out of range."""
        pages = parse_page_range("20-30", 10)
        assert pages == []

    def test_edge_case_page_1(self):
        """Test page 1 specifically."""
        pages = parse_page_range("1", 10)
        assert pages == [1]

    def test_edge_case_last_page(self):
        """Test last page specifically."""
        pages = parse_page_range("10", 10)
        assert pages == [10]

    def test_range_to_last(self):
        """Test range ending at last page."""
        pages = parse_page_range("8-", 10)
        assert pages == [8, 9, 10]

    def test_range_from_first(self):
        """Test range starting from first page."""
        pages = parse_page_range("-5", 10)
        assert pages == [1, 2, 3, 4, 5]
