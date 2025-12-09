# Typst Templates for xtctool

This directory contains Jinja2 templates for rendering Typst documents.

## Available Templates

### default.typ.jinja
The default template with configurable fonts, margins, and markdown inclusion via cmarker.

**Parameters:**
- `font` - Font family (default: "Liberation Serif")
- `font_size` - Font size in points (default: 11)
- `margin` - Page margin in points (default: 20)
- `line_spacing` - Line spacing multiplier (default: 1.2)
- `justify` - Text justification (default: true)
- `markdown_file` - Path to markdown file to render with cmarker
- `content` - Direct Typst content if not using markdown_file

**Automatic parameters** (provided by MarkdownFileAsset):
- `width_pt`, `height_pt` - Page dimensions in points
- `width_px`, `height_px` - Page dimensions in pixels
- `ppi` - Pixels per inch

## Architecture

Templates are used by the `MarkdownFileAsset` class to wrap markdown content in Typst formatting. The workflow is:

1. **MarkdownFileAsset** receives a .md file
2. Creates a temporary working directory
3. Copies the markdown file to the temp directory
4. Renders the Jinja2 template with configuration variables
5. Writes the rendered Typst source to temp directory
6. Uses **TypstRenderer** to compile the Typst source
7. Returns an **ImageAsset** with the rendered result

## Creating Custom Templates

Templates use Jinja2 syntax and render to Typst markup.

### Example: Custom Template

```jinja
{# my-template.typ.jinja #}
#set page(width: {{ width_pt }}pt, height: {{ height_pt }}pt, margin: {{ margin }}pt)
#set text(font: "{{ font }}", size: {{ font_size }}pt, fill: rgb("{{ color }}"))

#align(center)[
  #text(size: {{ title_size }}pt)[*{{ title }}*]
]

#v(1em)

{% if markdown_file %}
#import "@preview/cmarker:0.1.7"

#cmarker.render(read("{{ markdown_file }}"))
{% endif %}
```

### Configuration via config.toml

Templates are configured through the `[typst]` section of your config file:

```toml
[typst]
ppi = 144.0
template = "default.typ.jinja"  # or "my-template.typ.jinja"
font = "Liberation Serif"
font_size = 12
margin = 20
line_spacing = 1.2
justify = true
```

### Usage with Assets API

```python
from xtctool.assets import MarkdownFileAsset

config = {
    'output': {'width': 480, 'height': 800},
    'typst': {
        'ppi': 144.0,
        'template': 'my-template.typ.jinja',
        'font': 'Arial',
        'font_size': 12,
        'margin': 15,
    }
}

asset = MarkdownFileAsset('content.md')
image_asset = asset.convert(config)
```

## Tips

1. Use `{{ variable|default('value') }}` for optional parameters with defaults
2. All page dimension variables (width_pt, height_pt, etc.) are always available
3. Use cmarker to render markdown: `#cmarker.render(read("{{ markdown_file }}"))`
4. Boolean values from Python are automatically converted to lowercase strings for Typst
5. Test your templates by creating a MarkdownFileAsset and calling convert()
