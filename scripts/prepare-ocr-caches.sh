#!/bin/sh
set -eu

scripts/ocr-pdf.sh abc-main "Sources/[www.tcfca.com]-ABC TCF/ABC-TCF-www.tcfca.com.pdf"
scripts/ocr-pdf.sh boursin "Sources/[www.tcfca.com]-Boursin J.-L. - Test de connaissance du francais/Boursin J.-L. - Test de connaissance du francais - 2008-www.tcfca.com.pdf"
scripts/ocr-pdf.sh intensif "Sources/[www.tcfca.com]-TCF-Entrainement-Intensif/TCF-Entrainement-Intensif-www.tcfca.com.pdf"
scripts/ocr-pdf.sh tv5monde "Sources/TV5Monde Entraînement-www.tcfca.com/TV5Monde Entraînement-www.tcfca.com.pdf"

if [ -x .venv/bin/python ]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi

"$PYTHON" scripts/prepare-abc-pdf-assets.py
