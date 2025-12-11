wget https://www.gutenberg.org/ebooks/1661.epub3.images -O pg1661-images-3.epub

cat > config.toml <<EOF
[typst]
font = "Libertinus Serif"
font_size = 22
show_page_numbers = true
page_number_style = "bar"  # Options: "plain" (just number), "fraction" (1/10), "bar" (progress bar)
page_number_size = 16  # Font size for page numbers (in points)
line_spacing = 0.5
justify = true
EOF

pandoc pg1661-images-3.epub -t commonmark --extract-media . -o pg1661-images-3.md
xtctool convert -c config.toml pg1661-images-3.md:125 -o pg1661-images-3.png