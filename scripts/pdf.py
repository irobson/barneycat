"""Render report.md to report.pdf with pure wheels, so it works the same on every system."""

from __future__ import annotations

from pathlib import Path

STYLE = """
body { font-family: sans-serif; font-size: 10.5pt; line-height: 1.4; }
h1 { font-size: 20pt; margin-bottom: 4pt; }
h2 { font-size: 14pt; margin-top: 16pt; }
h3 { font-size: 11.5pt; margin-top: 12pt; }
blockquote { margin-left: 12pt; color: #444444; font-style: italic; }
code { font-family: monospace; }
th, td { padding: 3pt 6pt; text-align: left; }
"""
PAGE = (0, 0, 595, 842)
MARGIN = 48


def render(folder: Path) -> Path:
    import markdown
    import pymupdf

    source = folder / "report.md"
    if not source.exists():
        raise SystemExit(f"report not found: {source}")
    html = markdown.markdown(source.read_text(encoding="utf-8"), extensions=["tables", "sane_lists"])

    story = pymupdf.Story(html=html, user_css=STYLE, archive=pymupdf.Archive(str(folder)))
    target = folder / "report.pdf"
    writer = pymupdf.DocumentWriter(str(target))
    area = pymupdf.Rect(*PAGE) + (MARGIN, MARGIN, -MARGIN, -MARGIN)
    more = True
    while more:
        device = writer.begin_page(pymupdf.Rect(*PAGE))
        more, _ = story.place(area)
        story.draw(device)
        writer.end_page()
    writer.close()
    return target
