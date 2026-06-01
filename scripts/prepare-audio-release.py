"""
Prepare audio files for a GitHub Release.

The web app fetches audio as:
    {NEXT_PUBLIC_AUDIO_BASE_URL}/{sha256}.mp3

This script reads the audio asset table from the catalog, copies every MP3
into an output directory renamed to its SHA-256 hash, and prints upload
instructions for creating a GitHub Release.

Usage:
    python scripts/prepare-audio-release.py [--out-dir audio-release]

Then upload the contents of audio-release/ to a GitHub Release and set the
repository variable AUDIO_BASE_URL to:
    https://github.com/OWNER/REPO/releases/download/TAG
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "content" / "generated" / "catalog.sqlite"


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy hashed audio files for GitHub Release upload.")
    parser.add_argument("--out-dir", default="audio-release", help="Output directory (default: audio-release)")
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if not DB.exists():
        raise SystemExit(f"Catalog not found at {DB}. Run 'npm run build-catalog' first.")

    connection = sqlite3.connect(DB)
    rows = connection.execute("SELECT hash, path FROM audio_assets ORDER BY path").fetchall()
    connection.close()

    copied = 0
    missing = 0
    for asset_hash, path_str in rows:
        source = ROOT / path_str
        if not source.exists():
            print(f"  MISSING: {path_str}")
            missing += 1
            continue
        target = out / f"{asset_hash}.mp3"
        if not target.exists():
            shutil.copy2(source, target)
            copied += 1
        else:
            copied += 1  # already there from a previous run

    total = copied + missing
    print(f"\nAudio release prepared: {out}/")
    print(f"  {copied}/{total} files copied  ({missing} source files missing)")
    print()
    print("Next steps:")
    print("  1. Create a GitHub Release (e.g. tag: audio-v1)")
    print(f"  2. Upload all {copied} .mp3 files from {out}/")
    print("  3. In the repo Settings → Variables → Actions, set:")
    print("       AUDIO_BASE_URL = https://github.com/OWNER/REPO/releases/download/audio-v1")
    print("  4. Re-run the GitHub Pages deployment workflow.")


if __name__ == "__main__":
    main()
