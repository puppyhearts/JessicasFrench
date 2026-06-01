from __future__ import annotations

from pydantic import BaseModel


class ChoiceOut(BaseModel):
    label: str
    text: str


class QuestionOut(BaseModel):
    id: int
    series_number: int
    question_number: int
    section: str
    prompt: str
    instructions: str | None
    correct_answer: str | None
    audio_path: str | None
    audio_start_seconds: float | None
    audio_end_seconds: float | None
    choices: list[ChoiceOut]


class AttemptIn(BaseModel):
    selected_answer: str


class AttemptOut(BaseModel):
    is_correct: bool
    selected_answer: str
    correct_answer: str | None
