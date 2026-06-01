from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'tcf.db'}")
SOURCE_ROOT = Path(os.getenv("SOURCE_ROOT", str(ROOT / "Sources")))
GENERATED_ROOT = Path(os.getenv("GENERATED_ROOT", str(ROOT / "content" / "generated")))

