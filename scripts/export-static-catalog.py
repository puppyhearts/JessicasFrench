from __future__ import annotations

import json
import hashlib
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "content" / "generated" / "catalog.sqlite"
PUBLIC = ROOT / "apps" / "web" / "public" / "catalog"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    images = PUBLIC / "images"
    images.mkdir(exist_ok=True)
    for stale_image in images.glob("*.png"):
        stale_image.unlink()
    connection = sqlite3.connect(CATALOG)
    connection.row_factory = sqlite3.Row
    collections = [dict(row) for row in connection.execute(
        "SELECT slug, name, website, question_count, published_count FROM collections ORDER BY name"
    )]
    questions: list[dict] = []
    for row in connection.execute("SELECT * FROM questions WHERE published = 1 ORDER BY collection_slug, group_label, question_number"):
        question_id = row["stable_id"]
        choices = [dict(choice) for choice in connection.execute(
            "SELECT label, text FROM answer_choices WHERE question_id = ? ORDER BY label", (question_id,)
        )]
        occurrences = [dict(occurrence) for occurrence in connection.execute(
            "SELECT website, group_label, question_number, source_page, source_exercise FROM question_occurrences WHERE question_id = ? ORDER BY website, group_label, question_number",
            (question_id,),
        )]
        audio = connection.execute(
            "SELECT qa.audio_hash AS asset_id, qa.start_seconds, qa.end_seconds, aa.duration_seconds FROM question_audio qa JOIN audio_assets aa ON aa.hash = qa.audio_hash WHERE qa.question_id = ?",
            (question_id,),
        ).fetchone()
        transcript = connection.execute(
            "SELECT text, words_json FROM audio_transcripts WHERE audio_hash = (SELECT audio_hash FROM question_audio WHERE question_id = ?)",
            (question_id,),
        ).fetchone()
        image = connection.execute("SELECT image_path FROM question_assets WHERE question_id = ?", (question_id,)).fetchone()
        image_url = None
        if image and Path(image["image_path"]).exists():
            src = Path(image["image_path"])
            digest = hashlib.sha256(str(src.resolve()).encode("utf-8")).hexdigest()[:12]
            target = images / f"{digest}-{src.name}"
            if src.resolve() != target.resolve():
                shutil.copy2(src, target)
            image_url = f"catalog/images/{target.name}"
        questions.append({
            "id": question_id, "collection": row["collection_slug"], "group_label": row["group_label"],
            "question_number": row["question_number"], "display_label": row["display_label"], "section": row["section"],
            "level": row["level"], "difficulty_rank": row["difficulty_rank"], "prompt": row["prompt"],
            "instructions": row["instructions"], "correct_answer": row["correct_answer"],
            "transcript": transcript["text"] if transcript else row["transcript"],
            "transcript_words": json.loads(transcript["words_json"]) if transcript else [],
            "choices": choices, "occurrences": occurrences, "audio": dict(audio) if audio else None,
            "has_image": bool(image_url), "image_url": image_url,
        })
    connection.close()
    write_json(PUBLIC / "collections.json", collections)
    write_json(PUBLIC / "questions.json", questions)
    write_json(PUBLIC / "transcripts.json", {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((PUBLIC / "transcripts").glob("*.json"))
    })


if __name__ == "__main__":
    main()
