#!/bin/sh
set -eu

if [ -x .venv/bin/python ]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi

"$PYTHON" -m apps.api.app.ingest --source-root Sources --generated-root content/generated
