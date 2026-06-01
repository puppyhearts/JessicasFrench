from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.api.app.source_extractors import ABC_PDF_PAGES


SOURCE = ROOT / ".ocr-cache" / "abc-main" / "images"
TARGET = ROOT / ".ocr-cache" / "abc-pdf-assets"


def safe_group(group: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", group.lower()).strip("-")


def copy_page(group: str, page: int) -> None:
    source = SOURCE / f"page-{page:03d}.png"
    if not source.exists():
        raise FileNotFoundError(f"Required ABC OCR page is missing: {source}")
    target = TARGET / f"{safe_group(group)}-page-{page:03d}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


def main() -> None:
    for group, pages in ABC_PDF_PAGES.items():
        for page in pages:
            copy_page(group, page)
    print(f"Generated {sum(len(pages) for pages in ABC_PDF_PAGES.values())} ABC PDF page images in {TARGET}")


if __name__ == "__main__":
    main()
