"""PDF to bitmap converter using PyMuPDF (fitz)."""

from PIL import Image
import fitz  # PyMuPDF


class PDFConverter:
    """Convert PDF pages to bitmap images using PyMuPDF."""

    def __init__(self, resolution: int = 144):
        """Initialize PDF converter.

        Args:
            resolution: DPI resolution for rendering (default: 144)
        """
        self.resolution = resolution
        # Calculate zoom factor from DPI (72 DPI is default)
        self.zoom = resolution / 72.0

    def get_page_count(self, pdf_path: str) -> int:
        """Get number of pages in PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages
        """
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        return page_count

    def render_page(self, pdf_path: str, page_num: int) -> Image.Image:
        """Render a single PDF page to bitmap image.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)

        Returns:
            PIL Image object
        """
        doc = fitz.open(pdf_path)

        # Convert to 0-indexed
        page_idx = page_num - 1

        if page_idx < 0 or page_idx >= len(doc):
            doc.close()
            raise ValueError(f"Page {page_num} out of range (1-{len(doc)})")

        page = doc[page_idx]

        # Create transformation matrix for zoom
        mat = fitz.Matrix(self.zoom, self.zoom)

        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image
        # PyMuPDF pixmap is in RGB format
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        doc.close()

        return img
