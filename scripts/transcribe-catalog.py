from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import mlx_whisper


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "content" / "generated" / "catalog.sqlite"
DEFAULT_CACHE = ROOT / "apps" / "web" / "public" / "catalog" / "transcripts"
DEFAULT_MODEL = "mlx-community/whisper-small-mlx"


def normalized_words(result: dict) -> list[dict]:
    words: list[dict] = []
    for segment in result.get("segments", []):
        for word in segment.get("words", []):
            text = str(word.get("word", "")).strip()
            if text:
                words.append({"text": text, "start": round(float(word["start"]), 3), "end": round(float(word["end"]), 3)})
    return words


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate cached timed transcripts for published listening assets.")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--cache", default=str(DEFAULT_CACHE))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(args.catalog)
    rows = connection.execute(
        """
        SELECT DISTINCT aa.hash, aa.path
        FROM audio_assets aa
        JOIN question_audio qa ON qa.audio_hash = aa.hash
        JOIN questions q ON q.stable_id = qa.question_id
        WHERE q.published = 1 AND q.section = 'listening'
        ORDER BY aa.path
        """
    ).fetchall()
    if args.limit:
        rows = rows[:args.limit]

    connection.execute(
        "CREATE TABLE IF NOT EXISTS audio_transcripts (audio_hash TEXT PRIMARY KEY, text TEXT NOT NULL, words_json TEXT NOT NULL)"
    )
    for index, (asset_hash, audio_path) in enumerate(rows, start=1):
        output = cache / f"{asset_hash}.json"
        if output.exists():
            payload = json.loads(output.read_text(encoding="utf-8"))
        else:
            print(f"[{index}/{len(rows)}] {audio_path}", flush=True)
            result = mlx_whisper.transcribe(audio_path, path_or_hf_repo=args.model, language="fr", word_timestamps=True)
            payload = {"text": str(result.get("text", "")).strip(), "words": normalized_words(result)}
            output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        connection.execute(
            "INSERT OR REPLACE INTO audio_transcripts(audio_hash, text, words_json) VALUES (?, ?, ?)",
            (asset_hash, payload.get("text", ""), json.dumps(payload.get("words", []), ensure_ascii=False)),
        )
        connection.commit()
    connection.close()


if __name__ == "__main__":
    main()
