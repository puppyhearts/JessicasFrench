from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import GENERATED_ROOT


def catalog_path() -> Path:
    return GENERATED_ROOT / "catalog.sqlite"


def connect_catalog() -> sqlite3.Connection:
    path = catalog_path()
    if not path.exists():
        raise FileNotFoundError("Generated catalog not found. Run npm run build-catalog.")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def manifest() -> dict:
    path = GENERATED_ROOT / "manifest.json"
    if not path.exists():
        raise FileNotFoundError("Generated manifest not found. Run npm run build-catalog.")
    return json.loads(path.read_text(encoding="utf-8"))


def collections() -> list[dict]:
    with connect_catalog() as connection:
        rows = connection.execute(
            "SELECT slug, name, website, question_count, published_count FROM collections ORDER BY name"
        ).fetchall()
    return [dict(row) for row in rows]


def _question(connection: sqlite3.Connection, row: sqlite3.Row) -> dict:
    choices = [
        dict(choice)
        for choice in connection.execute(
            "SELECT label, text FROM answer_choices WHERE question_id = ? ORDER BY label", (row["stable_id"],)
        ).fetchall()
    ]
    occurrences = [
        dict(occurrence)
        for occurrence in connection.execute(
            """
            SELECT website, group_label, question_number, source_page, source_exercise
            FROM question_occurrences WHERE question_id = ? ORDER BY website, group_label, question_number
            """,
            (row["stable_id"],),
        ).fetchall()
    ]
    audio = connection.execute(
        """
        SELECT qa.audio_hash AS asset_id, qa.start_seconds, qa.end_seconds, aa.duration_seconds, aa.path
        FROM question_audio qa JOIN audio_assets aa ON aa.hash = qa.audio_hash
        WHERE qa.question_id = ?
        """,
        (row["stable_id"],),
    ).fetchone()
    transcript = connection.execute(
        """
        SELECT text, words_json FROM audio_transcripts
        WHERE audio_hash = (SELECT audio_hash FROM question_audio WHERE question_id = ?)
        """,
        (row["stable_id"],),
    ).fetchone()
    image = connection.execute("SELECT image_path FROM question_assets WHERE question_id = ?", (row["stable_id"],)).fetchone()
    return {
        "id": row["stable_id"],
        "collection": row["collection_slug"],
        "group_label": row["group_label"],
        "question_number": row["question_number"],
        "display_label": row["display_label"],
        "section": row["section"],
        "level": row["level"],
        "difficulty_rank": row["difficulty_rank"],
        "prompt": row["prompt"],
        "instructions": row["instructions"],
        "correct_answer": row["correct_answer"],
        "transcript": transcript["text"] if transcript else row["transcript"],
        "transcript_words": json.loads(transcript["words_json"]) if transcript else [],
        "mapping_status": row["mapping_status"],
        "published": bool(row["published"]),
        "choices": choices,
        "occurrences": occurrences,
        "audio": {**dict(audio), "extension": Path(audio["path"]).suffix.lower().lstrip(".")} if audio else None,
        "has_image": bool(image),
    }


def questions(
    collection: str | None = None,
    section: str | None = None,
    q_min: int | None = None,
    q_max: int | None = None,
    published: bool = True,
) -> list[dict]:
    clauses = ["published = ?"]
    params: list[object] = [int(published)]
    if collection:
        clauses.append("collection_slug = ?")
        params.append(collection)
    if section:
        clauses.append("section = ?")
        params.append(section)
    if q_min is not None:
        clauses.append("question_number >= ?")
        params.append(q_min)
    if q_max is not None:
        clauses.append("question_number <= ?")
        params.append(q_max)
    query = f"SELECT * FROM questions WHERE {' AND '.join(clauses)} ORDER BY collection_slug, group_label, question_number"
    with connect_catalog() as connection:
        return [_question(connection, row) for row in connection.execute(query, params).fetchall()]


def question(question_id: str) -> dict | None:
    with connect_catalog() as connection:
        row = connection.execute("SELECT * FROM questions WHERE stable_id = ?", (question_id,)).fetchone()
        return _question(connection, row) if row else None


def audio_path(asset_id: str) -> Path | None:
    with connect_catalog() as connection:
        row = connection.execute("SELECT path FROM audio_assets WHERE hash = ?", (asset_id,)).fetchone()
    return Path(row["path"]) if row else None


def image_path(question_id: str) -> Path | None:
    with connect_catalog() as connection:
        row = connection.execute("SELECT image_path FROM question_assets WHERE question_id = ?", (question_id,)).fetchone()
    return Path(row["image_path"]) if row else None
