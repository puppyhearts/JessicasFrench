#!/bin/sh
set -eu

if [ -x .venv/bin/python ]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi

"$PYTHON" scripts/export-static-catalog.py
