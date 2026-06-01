from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .parser import parse_pdf
from .source_extractors import ABC_ANSWERS, BOURSIN_VERIFIED_KEYS, INTENSIF_ANSWERS, REUSSIR_ANSWERS, TV5_ANSWERS, extract_boursin, extract_intensif_choices, spoken_choices


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_ROOT = ROOT / "Sources"
DEFAULT_GENERATED_ROOT = ROOT / "content" / "generated"
TRANSCRIPT_ROOT = ROOT / "apps" / "web" / "public" / "catalog" / "transcripts"


@dataclass
class QuestionSeed:
    stable_id: str
    collection_slug: str
    group_label: str
    question_number: int
    display_label: str
    section: str = "listening"
    level: str | None = None
    prompt: str | None = None
    instructions: str | None = None
    correct_answer: str | None = None
    choices: list[tuple[str, str]] | None = None
    audio_hash: str | None = None
    audio_start: float | None = None
    audio_end: float | None = None
    transcript: str | None = None
    difficulty_rank: int | None = None
    image_path: str | None = None
    source_page: int | None = None
    source_exercise: str | None = None
    mapping_status: str = "mapped"


COLLECTIONS = {
    "tv5monde": ("TV5Monde Entraînement", "TV5Monde / tcfca.com"),
    "abc-tcf": ("ABC TCF", "ABC TCF / tcfca.com"),
    "boursin": ("Boursin J.-L.", "Boursin J.-L. / tcfca.com"),
    "official-guide": ("Guide officiel d'entraînement au TCF", "Guide officiel / tcfca.com"),
    "reussir-tcf": ("Réussir le TCF", "Réussir le TCF / tcfca.com"),
    "tcf-250": ("TCF 250 Activités", "TCF 250 Activités / tcfca.com"),
    "intensif": ("TCF Entraînement Intensif", "TCF Entraînement Intensif / tcfca.com"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        check=True,
        text=True,
    )
    return round(float(result.stdout.strip()), 3)


def pdf_pages(path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], capture_output=True, check=True, text=True)
    match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.M)
    return int(match.group(1)) if match else 0


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE collections (
          slug TEXT PRIMARY KEY, name TEXT NOT NULL, website TEXT NOT NULL,
          question_count INTEGER NOT NULL DEFAULT 0, published_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE source_documents (
          hash TEXT PRIMARY KEY, collection_slug TEXT NOT NULL, path TEXT NOT NULL,
          page_count INTEGER NOT NULL, aliases_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE audio_assets (
          hash TEXT PRIMARY KEY, path TEXT NOT NULL, duration_seconds REAL NOT NULL,
          aliases_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE audio_transcripts (
          audio_hash TEXT PRIMARY KEY, text TEXT NOT NULL, words_json TEXT NOT NULL
        );
        CREATE TABLE questions (
          stable_id TEXT PRIMARY KEY, collection_slug TEXT NOT NULL, group_label TEXT NOT NULL,
          question_number INTEGER NOT NULL, display_label TEXT NOT NULL, section TEXT NOT NULL,
          level TEXT, difficulty_rank INTEGER NOT NULL, prompt TEXT, instructions TEXT, correct_answer TEXT, transcript TEXT,
          mapping_status TEXT NOT NULL, published INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE answer_choices (
          question_id TEXT NOT NULL, label TEXT NOT NULL, text TEXT NOT NULL,
          PRIMARY KEY(question_id, label)
        );
        CREATE TABLE question_audio (
          question_id TEXT PRIMARY KEY, audio_hash TEXT NOT NULL,
          start_seconds REAL, end_seconds REAL
        );
        CREATE TABLE question_assets (
          question_id TEXT PRIMARY KEY, image_path TEXT NOT NULL
        );
        CREATE TABLE question_occurrences (
          id INTEGER PRIMARY KEY AUTOINCREMENT, question_id TEXT NOT NULL,
          collection_slug TEXT NOT NULL, website TEXT NOT NULL, group_label TEXT NOT NULL,
          question_number INTEGER NOT NULL, source_page INTEGER, source_exercise TEXT
        );
        CREATE TABLE validation_issues (
          id INTEGER PRIMARY KEY AUTOINCREMENT, severity TEXT NOT NULL, collection_slug TEXT,
          question_id TEXT, code TEXT NOT NULL, message TEXT NOT NULL
        );
        """
    )


def collection_for(path: Path) -> str:
    text = str(path)
    if "ABC TCF" in text:
        return "abc-tcf"
    if "Boursin" in text:
        return "boursin"
    if "Guide officiel" in text:
        return "official-guide"
    if "Reussir le TCF" in text:
        return "reussir-tcf"
    if "TCF 250" in text:
        return "tcf-250"
    if "TCF-Entrainement-Intensif" in text:
        return "intensif"
    return "tv5monde"


def qid(collection: str, group: str, number: int) -> str:
    safe_group = re.sub(r"[^a-z0-9]+", "-", group.lower()).strip("-")
    return f"{collection}:{safe_group}:q{number:03d}"


def expand_numbers(raw: str) -> list[int]:
    return [int(number) for number in re.findall(r"\d+", raw)]


def difficulty_rank(seed: QuestionSeed) -> int:
    level = (seed.level or "").upper()
    level_match = re.search(r"([ABC])([12])|N([1-6])", level)
    if level_match:
        if level_match.group(3):
            return int(level_match.group(3))
        return {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}[level]
    return max(1, min(6, (seed.question_number - 1) // 20 + 1))


def map_abc(path: Path, asset_hash: str) -> list[QuestionSeed]:
    name = path.name
    mock = re.search(r"TCFblanc_question(\d+)", name, re.I)
    if mock:
        number = int(mock.group(1))
        group = "Test blanc"
        return [
            QuestionSeed(
                qid("abc-tcf", group, number), "abc-tcf", group, number, f"Q{number}",
                audio_hash=asset_hash, prompt="Écoutez l'enregistrement puis choisissez la bonne proposition.",
                choices=spoken_choices(), correct_answer=ABC_ANSWERS[group][number],
            )
        ]
    match = re.search(r"CO_questions?\s*(\d+(?:_\d+)*)", name, re.I)
    if not match:
        return []
    numbers = expand_numbers(match.group(1))
    return [
        QuestionSeed(
            qid("abc-tcf", "Compréhension orale", number), "abc-tcf", "Compréhension orale",
            number, f"Q{number}", audio_hash=asset_hash,
            prompt="Écoutez l'enregistrement puis choisissez la bonne proposition.",
            choices=spoken_choices(), correct_answer=ABC_ANSWERS["Compréhension orale"][number],
            mapping_status="needs_audio_split" if len(numbers) > 1 else "mapped",
        )
        for number in numbers
    ]


def map_boursin(path: Path, asset_hash: str) -> list[QuestionSeed]:
    name = path.name
    match = re.search(r"niveau(\d+)-(consignes|situation|enregistrement)(\d+)?", name, re.I)
    if not match or match.group(2).lower() == "consignes":
        return []
    level, _, raw_number = match.groups()
    number = int(raw_number or 0)
    group = f"Niveau {level}"
    key = (int(level), number)
    extracted = extract_boursin().get(key) if key in BOURSIN_VERIFIED_KEYS else None
    return [
        QuestionSeed(
            qid("boursin", group, number), "boursin", group, number, f"Q{number}",
            level=f"N{level}", audio_hash=asset_hash,
            prompt=extracted.prompt if extracted else None,
            choices=extracted.choices if extracted else None,
            correct_answer=extracted.correct_answer if extracted else None,
            source_page=extracted.source_page if extracted else None,
        )
    ]


def map_official(path: Path, asset_hash: str) -> list[QuestionSeed]:
    match = re.match(r"(\d+)-AudioTrack", path.name, re.I)
    if not match:
        return []
    number = int(match.group(1))
    group = "Audio tracks"
    return [QuestionSeed(qid("official-guide", group, number), "official-guide", group, number, f"Track {number}", audio_hash=asset_hash, mapping_status="needs_pdf_alignment")]


def map_reussir(path: Path, asset_hash: str) -> list[QuestionSeed]:
    match = re.search(r"([ABC][12])Q(\d+(?:-\d+)*)", path.name, re.I)
    if not match:
        return []
    level = match.group(1).upper()
    numbers = expand_numbers(match.group(2))
    return [
        QuestionSeed(
            qid("reussir-tcf", level, number), "reussir-tcf", level, number, f"{level} Q{number}",
            level=level, audio_hash=asset_hash,
            prompt="Écoutez l'enregistrement puis choisissez la bonne proposition." if number and level in REUSSIR_ANSWERS else None,
            choices=spoken_choices() if number and level in REUSSIR_ANSWERS else None,
            correct_answer=REUSSIR_ANSWERS.get(level, {}).get(number),
            mapping_status="needs_audio_split" if len(numbers) > 1 else "mapped",
        )
        for number in numbers
    ]


def map_tcf250(path: Path, asset_hash: str) -> list[QuestionSeed]:
    match = re.search(r"Exercise\s+(\d+)", path.name, re.I)
    if not match:
        return []
    number = int(match.group(1))
    group = "Activités"
    return [QuestionSeed(qid("tcf-250", group, number), "tcf-250", group, number, f"Q{number}", audio_hash=asset_hash)]


def map_intensif(path: Path, asset_hash: str) -> list[QuestionSeed]:
    match = re.search(r"TCF_Partie(\d+).*?_niv([ABC][12]).*?_p(\d+)_ex(\d+)", path.name, re.I)
    if not match:
        return []
    part, level, page, exercise = match.groups()
    number = int(exercise)
    group = f"{path.parent.name} · Partie {part}"
    source_group = "test1" if "Test1" in path.parent.name else "test2" if "Test2" in path.parent.name else "training"
    choices, source_page = extract_intensif_choices(source_group, int(page), number)
    return [
        QuestionSeed(
            qid("intensif", group, number), "intensif", group, number, f"Q{number}",
            level=level.upper(), audio_hash=asset_hash, source_page=source_page or int(page), source_exercise=exercise,
            prompt="Écoutez l'enregistrement puis choisissez la bonne réponse." if choices else None,
            choices=choices, correct_answer=INTENSIF_ANSWERS[source_group].get(number),
        )
    ]


def map_tv5(pdf: Path, audio_by_name: dict[str, str]) -> list[QuestionSeed]:
    seeds: list[QuestionSeed] = []
    for series in parse_pdf(pdf, ocr_fallback=True):
        audio_hash = audio_by_name.get(f"Entrainement - {series.number:02d}.mp3")
        for parsed in series.questions:
            group = f"Entraînement {series.number}"
            seeds.append(
                QuestionSeed(
                    qid("tv5monde", group, parsed.number), "tv5monde", group, parsed.number,
                    f"Q{parsed.number}", section=parsed.section, prompt=parsed.prompt,
                    instructions=parsed.instructions, correct_answer=TV5_ANSWERS.get(series.number, {}).get(parsed.number, parsed.correct_answer),
                    choices=[(choice.label, choice.text) for choice in parsed.choices],
                    audio_hash=audio_hash if parsed.section == "listening" else None,
                    image_path=str(ROOT / ".ocr-cache" / "tv5monde" / "images" / f"page-{parsed.page_number:03d}.png") if parsed.section == "reading" else None,
                    source_page=parsed.page_number, source_exercise=str(parsed.number),
                    mapping_status="needs_audio_alignment" if parsed.section == "listening" else "mapped",
                )
            )
    return seeds


MAPPERS = {
    "abc-tcf": map_abc,
    "boursin": map_boursin,
    "official-guide": map_official,
    "reussir-tcf": map_reussir,
    "tcf-250": map_tcf250,
    "intensif": map_intensif,
}


def upsert_seed(connection: sqlite3.Connection, seed: QuestionSeed) -> None:
    choices = seed.choices or []
    has_four_choices = len(choices) == 4
    published = int(bool(seed.prompt and has_four_choices and seed.correct_answer))
    connection.execute(
        """
        INSERT INTO questions(
          stable_id, collection_slug, group_label, question_number, display_label, section,
          level, difficulty_rank, prompt, instructions, correct_answer, transcript, mapping_status, published
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(stable_id) DO UPDATE SET
          prompt=COALESCE(excluded.prompt, questions.prompt),
          instructions=COALESCE(excluded.instructions, questions.instructions),
          correct_answer=COALESCE(excluded.correct_answer, questions.correct_answer),
          mapping_status=excluded.mapping_status,
          published=MAX(questions.published, excluded.published)
        """,
        (
            seed.stable_id, seed.collection_slug, seed.group_label, seed.question_number,
            seed.display_label, seed.section, seed.level, seed.difficulty_rank or difficulty_rank(seed), seed.prompt, seed.instructions,
            seed.correct_answer, seed.transcript, seed.mapping_status, published,
        ),
    )
    for label, text in choices:
        connection.execute(
            "INSERT OR REPLACE INTO answer_choices(question_id, label, text) VALUES (?, ?, ?)",
            (seed.stable_id, label, text),
        )
    if seed.audio_hash:
        connection.execute(
            "INSERT OR REPLACE INTO question_audio VALUES (?, ?, ?, ?)",
            (seed.stable_id, seed.audio_hash, seed.audio_start, seed.audio_end),
        )
    if seed.image_path and Path(seed.image_path).exists():
        connection.execute("INSERT OR REPLACE INTO question_assets VALUES (?, ?)", (seed.stable_id, seed.image_path))
    name, website = COLLECTIONS[seed.collection_slug]
    connection.execute(
        """
        INSERT INTO question_occurrences(
          question_id, collection_slug, website, group_label, question_number, source_page, source_exercise
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (seed.stable_id, seed.collection_slug, website, seed.group_label, seed.question_number, seed.source_page, seed.source_exercise),
    )


def add_validation_issues(connection: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    rows = connection.execute(
        """
        SELECT q.stable_id, q.collection_slug, q.prompt, q.correct_answer, q.mapping_status,
               COUNT(c.label) AS choice_count, qa.audio_hash
        FROM questions q
        LEFT JOIN answer_choices c ON c.question_id = q.stable_id
        LEFT JOIN question_audio qa ON qa.question_id = q.stable_id
        GROUP BY q.stable_id
        """
    ).fetchall()
    for question_id, collection, prompt, correct, status, choice_count, audio_hash in rows:
        issues: list[tuple[str, str]] = []
        if not prompt:
            issues.append(("missing_prompt", "Question prompt was not deterministically parsed from the supplied PDFs."))
        if choice_count != 4:
            issues.append(("missing_choices", f"Expected four answer choices; found {choice_count}."))
        if not correct:
            issues.append(("missing_answer", "Correct answer was not deterministically parsed from supplied correction pages."))
        if not audio_hash:
            issues.append(("missing_audio", "No question-level audio mapping is available."))
        if status.startswith("needs_"):
            issues.append((status, "Source mapping requires offline alignment before publication."))
        for code, message in issues:
            connection.execute(
                "INSERT INTO validation_issues(severity, collection_slug, question_id, code, message) VALUES ('warning', ?, ?, ?, ?)",
                (collection, question_id, code, message),
            )
            counts[code] += 1
    return dict(sorted(counts.items()))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_catalog(source_root: Path, generated_root: Path) -> dict[str, object]:
    temp_root = generated_root.with_name(f"{generated_root.name}.tmp")
    if temp_root.exists():
        shutil.rmtree(temp_root)
    temp_root.mkdir(parents=True)
    reports = temp_root / "reports"
    db_path = temp_root / "catalog.sqlite"
    connection = sqlite3.connect(db_path)
    create_schema(connection)
    for slug, (name, website) in COLLECTIONS.items():
        connection.execute("INSERT INTO collections(slug, name, website) VALUES (?, ?, ?)", (slug, name, website))

    pdfs = sorted(source_root.rglob("*.pdf"))
    audios = sorted(source_root.rglob("*.mp3"))
    pdf_groups: dict[str, list[Path]] = defaultdict(list)
    audio_groups: dict[str, list[Path]] = defaultdict(list)
    for path in pdfs:
        pdf_groups[sha256(path)].append(path)
    for path in audios:
        audio_groups[sha256(path)].append(path)

    for asset_hash, paths in pdf_groups.items():
        canonical = paths[0]
        connection.execute(
            "INSERT INTO source_documents VALUES (?, ?, ?, ?, ?)",
            (asset_hash, collection_for(canonical), str(canonical), pdf_pages(canonical), json.dumps([str(path) for path in paths[1:]], ensure_ascii=False)),
        )
    for asset_hash, paths in audio_groups.items():
        canonical = paths[0]
        connection.execute(
            "INSERT INTO audio_assets VALUES (?, ?, ?, ?)",
            (asset_hash, str(canonical), duration(canonical), json.dumps([str(path) for path in paths[1:]], ensure_ascii=False)),
        )
        transcript_path = TRANSCRIPT_ROOT / f"{asset_hash}.json"
        if transcript_path.exists():
            transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO audio_transcripts VALUES (?, ?, ?)",
                (asset_hash, transcript.get("text", ""), json.dumps(transcript.get("words", []), ensure_ascii=False)),
            )

    mapped_audio_hashes: set[str] = set()
    for asset_hash, paths in audio_groups.items():
        canonical = paths[0]
        collection = collection_for(canonical)
        mapper = MAPPERS.get(collection)
        if mapper:
            seeds = mapper(canonical, asset_hash)
            for seed in seeds:
                upsert_seed(connection, seed)
                mapped_audio_hashes.add(asset_hash)

    tv5_pdf = next(path for path in pdfs if collection_for(path) == "tv5monde")
    tv5_names = {paths[0].name: asset_hash for asset_hash, paths in audio_groups.items() if collection_for(paths[0]) == "tv5monde"}
    for seed in map_tv5(tv5_pdf, tv5_names):
        upsert_seed(connection, seed)
        if seed.audio_hash:
            mapped_audio_hashes.add(seed.audio_hash)

    for asset_hash, paths in audio_groups.items():
        if asset_hash not in mapped_audio_hashes:
            connection.execute(
                "INSERT INTO validation_issues(severity, collection_slug, code, message) VALUES ('warning', ?, 'unmapped_audio', ?)",
                (collection_for(paths[0]), f"Unmapped audio source: {paths[0]}"),
            )

    issue_counts = add_validation_issues(connection)
    for code, count in connection.execute("SELECT code, COUNT(*) FROM validation_issues GROUP BY code").fetchall():
        issue_counts[code] = count
    issue_counts = dict(sorted(issue_counts.items()))
    for slug in COLLECTIONS:
        question_count = connection.execute("SELECT COUNT(*) FROM questions WHERE collection_slug = ?", (slug,)).fetchone()[0]
        published_count = connection.execute("SELECT COUNT(*) FROM questions WHERE collection_slug = ? AND published = 1", (slug,)).fetchone()[0]
        connection.execute("UPDATE collections SET question_count = ?, published_count = ? WHERE slug = ?", (question_count, published_count, slug))
    connection.commit()

    collection_rows = connection.execute("SELECT slug, name, question_count, published_count FROM collections ORDER BY slug").fetchall()
    unresolved = connection.execute(
        "SELECT severity, collection_slug, question_id, code, message FROM validation_issues ORDER BY collection_slug, question_id, code"
    ).fetchall()
    connection.close()

    inventory = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_pdfs": len(pdfs),
        "unique_pdfs": len(pdf_groups),
        "duplicate_pdfs": len(pdfs) - len(pdf_groups),
        "raw_audio": len(audios),
        "unique_audio": len(audio_groups),
        "duplicate_audio": len(audios) - len(audio_groups),
    }
    manifest = {
        **inventory,
        "collections": [
            {"slug": slug, "name": name, "questions": questions, "published": published}
            for slug, name, questions, published in collection_rows
        ],
        "issue_counts": issue_counts,
        "unresolved_count": len(unresolved),
    }
    write_json(reports / "inventory.json", inventory)
    write_json(
        reports / "unresolved.json",
        [{"severity": severity, "collection": collection, "question_id": question, "code": code, "message": message}
         for severity, collection, question, code, message in unresolved],
    )
    write_json(temp_root / "manifest.json", manifest)
    if generated_root.exists():
        shutil.rmtree(generated_root)
    temp_root.rename(generated_root)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the one-time local TCF study catalog.")
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--generated-root", default=str(DEFAULT_GENERATED_ROOT))
    args = parser.parse_args()
    print(json.dumps(build_catalog(Path(args.source_root), Path(args.generated_root)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
