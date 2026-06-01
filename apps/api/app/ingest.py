from __future__ import annotations

import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from .database import Base, engine, session_scope
from .audio import segment_listening_track
from .models import AnswerChoice, AudioSegment, ExamSeries, IngestionRun, Question, Source
from .parser import ParsedQuestion, parse_pdf


AUDIO_RE = re.compile(r"Entrainement\s*-\s*(\d+)\.mp3$", re.I)


def audio_duration(path: Path) -> float:
    output = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return round(float(output), 3)


def audio_map(root: Path) -> dict[int, Path]:
    matched: dict[int, Path] = {}
    for path in root.rglob("*.mp3"):
        match = AUDIO_RE.search(path.name)
        if match:
            matched[int(match.group(1))] = path
    return matched


def upsert_question(session, series: ExamSeries, parsed: ParsedQuestion) -> Question:
    question = session.scalar(
        select(Question).where(Question.series_id == series.id, Question.question_number == parsed.number)
    )
    if question is None:
        question = Question(series_id=series.id, question_number=parsed.number)
        session.add(question)
    question.section = parsed.section
    question.prompt = parsed.prompt
    question.instructions = parsed.instructions
    question.correct_answer = parsed.correct_answer
    question.page_number = parsed.page_number
    question.confidence = parsed.confidence
    existing_choices = {choice.label: choice for choice in question.choices}
    parsed_labels = {choice.label for choice in parsed.choices}
    for choice in parsed.choices:
        stored_choice = existing_choices.get(choice.label)
        if stored_choice is None:
            question.choices.append(AnswerChoice(label=choice.label, text=choice.text))
        else:
            stored_choice.text = choice.text
    for label, stored_choice in existing_choices.items():
        if label not in parsed_labels:
            session.delete(stored_choice)
    return question


def ingest(source_root: Path, generated_root: Path, ocr_fallback: bool = True) -> dict[str, int]:
    generated_root.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    pdfs = sorted(source_root.rglob("*.pdf"))
    tracks = audio_map(source_root)
    summary = {"pdfs": len(pdfs), "audio_tracks": len(tracks), "series": 0, "questions": 0, "publishable_questions": 0}
    with session_scope() as session:
        run = IngestionRun(status="running")
        session.add(run)
        session.flush()
        source = session.scalar(select(Source).where(Source.slug == "tv5monde-tcfca"))
        if source is None:
            source = Source(slug="tv5monde-tcfca", name="TV5Monde Entraînement", root_path=str(source_root))
            session.add(source)
            session.flush()
        for pdf in pdfs:
            for parsed_series in parse_pdf(pdf, ocr_fallback=ocr_fallback):
                series = session.scalar(
                    select(ExamSeries).where(
                        ExamSeries.source_id == source.id, ExamSeries.series_number == parsed_series.number
                    )
                )
                if series is None:
                    series = ExamSeries(
                        source_id=source.id,
                        series_number=parsed_series.number,
                        title=f"TV5Monde Entraînement {parsed_series.number:02d}",
                        pdf_path=str(pdf),
                    )
                    session.add(series)
                    session.flush()
                track = tracks.get(parsed_series.number)
                series.title = f"TV5Monde Entraînement {parsed_series.number:02d}"
                series.pdf_path = str(pdf)
                series.pdf_start_page = parsed_series.start_page
                series.pdf_end_page = parsed_series.end_page
                series.audio_path = str(track) if track else None
                series.audio_duration_seconds = audio_duration(track) if track else None
                series.status = "parsed"
                listening_questions: dict[int, Question] = {}
                for question in parsed_series.questions:
                    stored = upsert_question(session, series, question)
                    if question.section == "listening":
                        listening_questions[question.number] = stored
                    summary["questions"] += 1
                    if question.correct_answer and len(question.choices) == 4:
                        summary["publishable_questions"] += 1
                session.flush()
                if track:
                    for number, segment in enumerate(segment_listening_track(track), start=1):
                        question = listening_questions.get(number)
                        if not question:
                            continue
                        if question.audio_segment is None:
                            question.audio_segment = AudioSegment()
                        question.audio_segment.start_seconds = segment.start_seconds
                        question.audio_segment.end_seconds = segment.end_seconds
                        question.audio_segment.confidence = segment.confidence
                summary["series"] += 1
        run.status = "completed"
        run.finished_at = datetime.utcnow()
        run.summary = summary
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest TCF PDF and audio sources.")
    parser.add_argument("--source-root", default="Sources")
    parser.add_argument("--generated-root", default="content/generated")
    parser.add_argument("--text-only", action="store_true", help="Skip OCR fallback for a faster development import.")
    args = parser.parse_args()
    import json

    print(json.dumps(ingest(Path(args.source_root), Path(args.generated_root), ocr_fallback=not args.text_only), indent=2))


if __name__ == "__main__":
    main()
