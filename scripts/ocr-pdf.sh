#!/bin/sh
set -eu

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "usage: scripts/ocr-pdf.sh <slug> <pdf> [--refresh-text]" >&2
  exit 2
fi

slug="$1"
pdf="$2"
root="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cache="$root/.ocr-cache/$slug"
images="$cache/images"
mkdir -p "$images"

if [ "${3:-}" = "--refresh-text" ]; then
  find "$images" -type f -name 'page-*.txt' -delete
fi

if ! find "$images" -type f -name 'page-*.png' | grep -q .; then
  pdftoppm -r 150 -png "$pdf" "$images/page"
fi

find "$images" -type f -name 'page-*.png' -print0 |
  xargs -0 -n 1 -P 6 sh -c '
    image="$1"
    output="${image%.*}.txt"
    if [ ! -s "$output" ]; then
      tesseract "$image" "${output%.txt}" -l fra >/dev/null 2>&1
    fi
  ' sh

echo "$cache"
