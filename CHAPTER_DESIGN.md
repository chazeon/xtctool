# Chapter/TOC Extraction Design

## Goal
Automatically extract table of contents from source files and convert to XTC chapters.

## Current Architecture

```
Source File → Asset Converter → ImageAsset → ... → XTFrameAsset → XTCWriter
```

### Files involved:
- `utils/typst.py`: TypstRenderer - compiles Typst to images
- `utils/pdf.py`: PDFConverter - renders PDF pages to images
- `assets/typst.py`: TypstFileAsset - orchestrates Typst conversion
- `assets/markdown.py`: MarkdownFileAsset - wraps markdown in Typst template
- `assets/pdf.py`: PDFAsset - orchestrates PDF conversion
- `cli/convert.py`: write_xtc() - creates XTC files with metadata
- `core/xtc.py`: XTCWriter - writes XTC format

## TOC Extraction Methods

### For Typst/Markdown (via Typst):
**Problem**: The `typst` Python library's `query()` function doesn't expose page numbers.

**Solution**: Compile to PDF first, then extract TOC using PyMuPDF:
```python
import typst
import fitz

# Step 1: Compile Typst to PDF (temporary)
typst.compile(file_path, output="/tmp/temp.pdf", format='pdf')

# Step 2: Extract TOC from PDF
doc = fitz.open("/tmp/temp.pdf")
toc = doc.get_toc()  # Returns [(level, title, page), ...]
doc.close()

# Step 3: Proceed with normal PNG rendering
# (existing code)
```

**Alternative**: Use `typst.query()` for structure but page numbers require workaround:
```python
import typst
import json

# Query headings (NO page numbers!)
result = typst.query(file_path, selector="heading")
headings = json.loads(result)

# Each heading has:
# - heading['level']: int (1, 2, 3...)
# - heading['body']['text']: heading text
# - NO page number field!
```

### For PDF:
Use PyMuPDF's built-in TOC:
```python
import fitz

doc = fitz.open(pdf_path)
toc = doc.get_toc()  # Returns [(level, title, page), ...]
doc.close()

# Example: [(1, "Chapter 1", 1), (2, "Section 1.1", 3), (1, "Chapter 2", 10)]
```

## Data Flow Design

### TOC Entry Structure
```python
@dataclass
class TOCEntry:
    """Table of contents entry."""
    title: str      # Heading text
    level: int      # 1=h1, 2=h2, etc.
    page: int       # Page number (1-based)
```

### Where to Extract:

**Option A: In utils layer (TypstRenderer, PDFConverter)**
- Pro: Single source of truth
- Con: Utilities should be simple

**Option B: In asset layer** ✓ RECOMMENDED
- Extract in TypstFileAsset, MarkdownFileAsset, PDFAsset
- Store as asset metadata: `toc: list[TOCEntry]`
- Propagate through conversion chain
- Pro: Keeps utilities focused, TOC travels with images

**Option C: At CLI level**
- Extract when writing XTC
- Con: Need to re-open source files

### Implementation Plan

1. **Add TOC extraction to utils:**
   ```python
   # utils/typst.py
   class TypstRenderer:
       def extract_toc(self, file_path: str) -> list[TOCEntry]:
           """Extract headings from Typst document."""
           # Use typst.query() to get headings

   # utils/pdf.py
   class PDFConverter:
       def extract_toc(self, pdf_path: str) -> list[TOCEntry]:
           """Extract TOC from PDF."""
           # Use fitz.Document.get_toc()
   ```

2. **Extract TOC in asset layer:**
   ```python
   # assets/typst.py, markdown.py
   class TypstFileAsset:
       def _convert_impl(self, config):
           # ... existing rendering ...

           # Extract TOC if enabled
           if config.get('extract_toc', True):
               toc = renderer.extract_toc(self.path)
               self.set_metadata('toc', toc)
   ```

3. **Store TOC in ImageAsset chain:**
   - TOC metadata propagates: FileAsset → ImageAsset → XTFrameAsset
   - Each asset can access via `self.get_metadata('toc')`

4. **Convert TOC to chapters at write time:**
   ```python
   # cli/convert.py - write_xtc()
   def toc_to_chapters(
       toc: list[TOCEntry],
       total_pages: int,
       chapter_level: int = 1,
       indent_sublevels: bool = True
   ) -> list[XTCChapter]:
       """Convert TOC entries to XTC chapters.

       Args:
           toc: List of TOC entries
           total_pages: Total page count
           chapter_level: Which heading level defines chapters (default: 1)
           indent_sublevels: Prefix lower levels with spaces

       Returns:
           List of XTCChapter objects
       """
       chapters = []

       # Filter to chapter-level headings
       chapter_entries = [e for e in toc if e.level == chapter_level]

       # Or include all levels with indentation:
       # for entry in toc:
       #     indent = "  " * (entry.level - 1) if indent_sublevels else ""
       #     title = f"{indent}{entry.title}"

       for i, entry in enumerate(chapter_entries):
           start_page = entry.page - 1  # Convert to 0-based

           # End page is before next chapter, or end of doc
           if i + 1 < len(chapter_entries):
               end_page = chapter_entries[i + 1].page - 2  # Exclusive end
           else:
               end_page = total_pages - 1

           chapters.append(XTCChapter(
               name=entry.title,
               start_page=start_page,
               end_page=end_page
           ))

       return chapters
   ```

5. **Update write_xtc() to use TOC:**
   ```python
   def write_xtc(output: str, frames: list[XTFrameAsset], cfg: dict[str, Any]):
       # ... existing metadata setup ...

       # Extract TOC from first frame (all have same TOC)
       chapters = None
       if frames and frames[0].get_metadata('toc'):
           toc = frames[0].get_metadata('toc')
           chapter_level = cfg.get('output', {}).get('chapter_level', 1)
           chapters = toc_to_chapters(toc, len(frames), chapter_level)

       writer = XTCWriter(
           # ... existing args ...
           chapters=chapters  # Add chapters!
       )
   ```

## Config Options

Add to `config.toml`:
```toml
[output]
# Chapter extraction
extract_toc = true           # Enable TOC extraction
chapter_level = 1            # Which heading level = chapter (1=h1, 2=h2, etc.)
chapter_indent = false       # Prefix sublevels with spaces
chapter_truncate = 79        # Max chapter name length (spec: 79 UTF-8 bytes)
```

## Edge Cases

1. **No TOC**: Document has no headings → chapters = None
2. **TOC but wrong level**: No h1 headings, only h2 → fallback to h2 or skip
3. **Multiple headings on same page**: Each gets own chapter (end_page = same as start_page)
4. **Long titles**: Truncate to 79 bytes, optionally add "..."
5. **Page selection**: If user selects pages 10-20, adjust TOC page numbers accordingly

## Typst Query Notes

The `typst` Python library supports queries:
```python
import typst

# Compile to document
doc = typst.compile(file_path, output=None)  # No output = return document

# Query for headings
headings = typst.query(doc, selector="heading")

# Access heading properties:
for h in headings:
    print(h.level)              # 1, 2, 3...
    print(h.body)               # text content
    print(h.location().page())  # page number (1-based)
```

## PyMuPDF TOC Notes

```python
import fitz

doc = fitz.open("file.pdf")
toc = doc.get_toc()  # Returns list of [level, title, page]

# Example:
# [
#   [1, "Introduction", 1],
#   [2, "Background", 2],
#   [1, "Methods", 5],
#   [2, "Experimental Setup", 6],
# ]
```

## Implementation Order

1. ✅ XTCChapter API already exists
2. [ ] Add `extract_toc()` to TypstRenderer
3. [ ] Add `extract_toc()` to PDFConverter
4. [ ] Extract TOC in asset layer, store in metadata
5. [ ] Add `toc_to_chapters()` helper
6. [ ] Update `write_xtc()` to use TOC
7. [ ] Add config options
8. [ ] Handle edge cases
9. [ ] Add tests

## Questions / Decisions

- **Which heading level for chapters?** Default to h1 (level=1), make configurable
- **Include all levels or just chapter level?** Start with chapter level only, can add indented sublevels later
- **Truncate long titles?** Yes, to 79 UTF-8 bytes (spec limit)
- **Add ellipsis "..." when truncating?** Optional, not essential for MVP
- **What if page selection changes page numbers?** Adjust TOC page numbers after selection applied
