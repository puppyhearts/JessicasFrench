from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    root_path: Mapped[str] = mapped_column(Text)
    series: Mapped[list["ExamSeries"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class ExamSeries(Base):
    __tablename__ = "exam_series"
    __table_args__ = (UniqueConstraint("source_id", "series_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    series_number: Mapped[int]
    title: Mapped[str] = mapped_column(String(255))
    pdf_path: Mapped[str] = mapped_column(Text)
    pdf_start_page: Mapped[int | None]
    pdf_end_page: Mapped[int | None]
    audio_path: Mapped[str | None] = mapped_column(Text)
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default="detected")
    source: Mapped[Source] = relationship(back_populates="series")
    questions: Mapped[list["Question"]] = relationship(back_populates="series", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("series_id", "question_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("exam_series.id", ondelete="CASCADE"))
    question_number: Mapped[int]
    section: Mapped[str] = mapped_column(String(30))
    prompt: Mapped[str] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    correct_answer: Mapped[str | None] = mapped_column(String(1))
    page_number: Mapped[int | None]
    confidence: Mapped[float] = mapped_column(Float, default=0)
    series: Mapped[ExamSeries] = relationship(back_populates="questions")
    choices: Mapped[list["AnswerChoice"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    audio_segment: Mapped["AudioSegment | None"] = relationship(back_populates="question", cascade="all, delete-orphan")


class AnswerChoice(Base):
    __tablename__ = "answer_choices"
    __table_args__ = (UniqueConstraint("question_id", "label"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(1))
    text: Mapped[str] = mapped_column(Text)
    question: Mapped[Question] = relationship(back_populates="choices")


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    selected_answer: Mapped[str] = mapped_column(String(1))
    is_correct: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AudioSegment(Base):
    __tablename__ = "audio_segments"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), unique=True)
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    question: Mapped[Question] = relationship(back_populates="audio_segment")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(40))
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
