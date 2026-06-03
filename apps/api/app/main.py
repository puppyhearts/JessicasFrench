from __future__ import annotations

import mimetypes

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from . import catalog
from .config import GENERATED_ROOT, SOURCE_ROOT
from .database import Base, SessionLocal, engine
from .ingest import ingest
from .models import Attempt, ExamSeries, IngestionRun, Question
from .schemas import AttemptIn, AttemptOut, ChoiceOut, QuestionOut


Base.metadata.create_all(engine)
app = FastAPI(title="French Audio Practice API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def question_out(question: Question) -> QuestionOut:
    return QuestionOut(
        id=question.id,
        series_number=question.series.series_number,
        question_number=question.question_number,
        section=question.section,
        prompt=question.prompt,
        instructions=question.instructions,
        correct_answer=question.correct_answer,
        audio_path=f"/api/audio/{question.series.id}" if question.series.audio_path else None,
        audio_start_seconds=question.audio_segment.start_seconds if question.audio_segment else None,
        audio_end_seconds=question.audio_segment.end_seconds if question.audio_segment else None,
        choices=[ChoiceOut(label=choice.label, text=choice.text) for choice in sorted(question.choices, key=lambda item: item.label)],
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/catalog")
def catalog_manifest():
    try:
        return catalog.manifest()
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error


@app.get("/api/collections")
def catalog_collections():
    try:
        return catalog.collections()
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error


@app.get("/api/catalog/questions")
def catalog_questions(
    collection: str | None = Query(default=None),
    section: str | None = Query(default=None),
    q_min: int | None = Query(default=None),
    q_max: int | None = Query(default=None),
    published: bool = Query(default=True),
):
    try:
        return catalog.questions(collection=collection, section=section, q_min=q_min, q_max=q_max, published=published)
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error


@app.get("/api/catalog/questions/{question_id:path}")
def catalog_question(question_id: str):
    try:
        record = catalog.question(question_id)
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    if record is None:
        raise HTTPException(404, "Question not found")
    return record


@app.post("/api/catalog/questions/{question_id:path}/attempts")
def catalog_attempt(question_id: str, body: AttemptIn):
    try:
        record = catalog.question(question_id)
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    if record is None:
        raise HTTPException(404, "Question not found")
    selected = body.selected_answer.upper()
    if selected not in {"A", "B", "C", "D"}:
        raise HTTPException(422, "Answer must be A, B, C or D")
    return {"selected_answer": selected, "correct_answer": record["correct_answer"], "is_correct": selected == record["correct_answer"]}


@app.get("/api/catalog/audio/{asset_id}")
def catalog_audio(asset_id: str):
    try:
        path = catalog.audio_path(asset_id)
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    if path is None or not path.exists():
        raise HTTPException(404, "Audio asset not found")
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream")


@app.get("/api/catalog/images/{question_id:path}")
def catalog_image(question_id: str):
    try:
        path = catalog.image_path(question_id)
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    if path is None or not path.exists():
        raise HTTPException(404, "Question image not found")
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream")


@app.get("/api/questions", response_model=list[QuestionOut])
def questions(
    series: int = Query(default=1),
    section: str | None = Query(default=None),
    include_incomplete: bool = Query(default=False),
    session: Session = Depends(db),
):
    query = (
        select(Question)
        .join(ExamSeries)
        .where(ExamSeries.series_number == series)
        .options(selectinload(Question.choices), selectinload(Question.series), selectinload(Question.audio_segment))
        .order_by(Question.question_number)
    )
    if section:
        query = query.where(Question.section == section)
    records = session.scalars(query).all()
    if not include_incomplete:
        records = [question for question in records if question.correct_answer and len(question.choices) == 4]
    return [question_out(question) for question in records]


@app.post("/api/questions/{question_id}/attempts", response_model=AttemptOut)
def attempt(question_id: int, body: AttemptIn, session: Session = Depends(db)):
    question = session.get(Question, question_id)
    if question is None:
        raise HTTPException(404, "Question not found")
    selected = body.selected_answer.upper()
    if selected not in {"A", "B", "C", "D"}:
        raise HTTPException(422, "Answer must be A, B, C or D")
    correct = selected == question.correct_answer if question.correct_answer else False
    session.add(Attempt(question_id=question.id, selected_answer=selected, is_correct=correct))
    session.commit()
    return AttemptOut(is_correct=correct, selected_answer=selected, correct_answer=question.correct_answer)


@app.get("/api/audio/{series_id}")
def audio(series_id: int, session: Session = Depends(db)):
    series = session.get(ExamSeries, series_id)
    if series is None or not series.audio_path or not Path(series.audio_path).exists():
        raise HTTPException(404, "Audio track not found")
    return FileResponse(series.audio_path, media_type="audio/mpeg")


@app.post("/api/ingestion/runs")
def start_ingestion():
    return ingest(SOURCE_ROOT, GENERATED_ROOT)


@app.get("/api/ingestion/runs")
def ingestion_runs(session: Session = Depends(db)):
    records = session.scalars(select(IngestionRun).order_by(desc(IngestionRun.id)).limit(20)).all()
    return [
        {
            "id": record.id,
            "status": record.status,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
            "summary": record.summary,
        }
        for record in records
    ]
