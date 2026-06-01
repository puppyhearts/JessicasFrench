#!/bin/sh
set -eu

if [ -x .venv/bin/python ]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi

for cache in abc-main boursin intensif tv5monde; do
  if ! find ".ocr-cache/$cache/images" -type f -name 'page-*.txt' 2>/dev/null | grep -q .; then
    echo "Missing required OCR cache: .ocr-cache/$cache" >&2
    echo "Run scripts/prepare-ocr-caches.sh before rebuilding the catalog." >&2
    exit 1
  fi
done

if [ ! -f .ocr-cache/abc-pdf-assets/ma-trise-des-structures-page-030.png ]; then
  "$PYTHON" scripts/prepare-abc-pdf-assets.py
fi

"$PYTHON" -m apps.api.app.catalog_builder --source-root Sources --generated-root content/generated
