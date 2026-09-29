"""Job-board HTML → readable plain text.

Descriptions are stored and shown as plain text only, so third-party HTML never reaches
the browser (no XSS surface). Block elements become line breaks and list items bullets.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from app.documents.extraction import normalize_text

_BLOCK = {
    "p", "div", "section", "article", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "table", "tr", "blockquote", "pre",
}  # fmt: skip
_SKIP = {"script", "style", "noscript", "template", "head"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP:
            self._skip_depth += 1
        elif tag == "li":
            self.parts.append("\n• ")
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK or tag == "li":
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(value: str | None, *, escaped: bool = False) -> str:
    """`escaped=True` for Greenhouse, whose `content` is entity-escaped HTML."""
    if not value:
        return ""
    source = html.unescape(value) if escaped else value
    parser = _TextExtractor()
    parser.feed(source)
    parser.close()
    text = normalize_text("".join(parser.parts))
    return re.sub(r"•\s*\n+", "• ", text)  # bullets whose text starts on the next line
