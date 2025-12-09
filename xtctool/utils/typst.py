"""Simple Typst compiler utility using the typst Python library."""

import tempfile
from pathlib import Path
from PIL import Image
import typst


class TypstRenderer:
    """Simple Typst to image renderer.

    This is a minimal wrapper around the typst library that compiles
    Typst source or files to PNG images. All complex orchestration
    (templates, multi-file projects, etc.) is handled in the assets layer.
    """

    def __init__(self, ppi: float = 144.0):
        """Initialize Typst renderer.

        Args:
            ppi: Pixels per inch for rendering (default: 144.0)
        """
        self.ppi = ppi

    def render_source(self, source: str) -> Image.Image:
        """Compile Typst source code to a PIL Image.

        Args:
            source: Typst markup source code

        Returns:
            PIL Image object

        Example:
            renderer = TypstRenderer(ppi=144.0)
            image = renderer.render_source('#set page(width: 480pt, height: 800pt)\\n= Hello')
        """
        # Create temporary files for compilation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.typ', delete=False, encoding='utf-8') as src_file:
            src_file.write(source)
            src_path = Path(src_file.name)

        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as out_file:
                out_path = Path(out_file.name)

            try:
                # Compile Typst source to PNG
                typst.compile(
                    str(src_path),
                    output=str(out_path),
                    format='png',
                    ppi=self.ppi
                )

                # Load and return image
                image = Image.open(out_path)
                # Make a copy so it's independent of the temp file
                image_copy = image.copy()
                image.close()

                return image_copy

            finally:
                # Clean up output file
                if out_path.exists():
                    out_path.unlink()
        finally:
            # Clean up source file
            if src_path.exists():
                src_path.unlink()

    def render_file(self, file_path: str, root_dir: str | None = None) -> list[Image.Image]:
        """Compile a Typst file to PIL Image(s).

        For multi-page documents, returns a list of images (one per page).
        For single-page documents, returns a list with one image.

        Args:
            file_path: Path to the Typst file
            root_dir: Optional root directory for resolving includes (default: file's directory)

        Returns:
            List of PIL Image objects (one per page)

        Raises:
            FileNotFoundError: If the file doesn't exist
            RuntimeError: If compilation fails

        Example:
            renderer = TypstRenderer(ppi=144.0)
            images = renderer.render_file('document.typ')
        """
        src_path = Path(file_path)
        if not src_path.exists():
            raise FileNotFoundError(f"Typst file not found: {file_path}")

        # Use file's directory as root if not specified
        if root_dir is None:
            root_dir = str(src_path.parent)

        # Create temp directory for output
        temp_dir = Path(tempfile.mkdtemp(prefix='typst_output_'))

        try:
            # Use pattern for multi-page output: output-{n}.png
            out_pattern = temp_dir / "page-{n}.png"

            # Compile Typst file to PNG(s)
            # Note: typst.compile will use root_dir for resolving #include paths
            typst.compile(
                str(src_path),
                output=str(out_pattern),
                format='png',
                ppi=self.ppi,
                root=root_dir
            )

            # Find all generated page files
            page_files = sorted(temp_dir.glob("page-*.png"))

            if not page_files:
                raise RuntimeError("No pages were generated")

            # Load all images
            images = []
            for page_file in page_files:
                image = Image.open(page_file)
                # Make a copy so it's independent of the temp file
                image_copy = image.copy()
                image.close()
                images.append(image_copy)

            return images

        except Exception as e:
            raise RuntimeError(f"Failed to compile Typst file: {e}") from e
        finally:
            # Clean up temp directory
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
