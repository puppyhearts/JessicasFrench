from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


SILENCE_RE = re.compile(r"silence_(start|end):\s*([0-9.]+)")


@dataclass
class Segment:
    start_seconds: float
    end_seconds: float
    confidence: float


def detect_silences(path: Path) -> list[tuple[float, float]]:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "silencedetect=noise=-35dB:d=0.7", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    silences: list[tuple[float, float]] = []
    start: float | None = None
    for kind, value in SILENCE_RE.findall(result.stderr):
        if kind == "start":
            start = float(value)
        elif start is not None:
            silences.append((start, float(value)))
            start = None
    return silences


def segment_listening_track(path: Path, expected_questions: int = 15) -> list[Segment]:
    silences = detect_silences(path)
    candidates = [(start, end) for start, end in silences if end - start >= 4]
    separators = sorted(candidates, key=lambda pair: pair[1] - pair[0], reverse=True)[: expected_questions - 1]
    if len(separators) < expected_questions - 1:
        return []
    separators.sort()
    duration = _duration(path)
    boundaries = [0.0] + [(start + end) / 2 for start, end in separators] + [duration]
    return [
        Segment(round(boundaries[index], 3), round(boundaries[index + 1], 3), 0.45)
        for index in range(expected_questions)
    ]


def _duration(path: Path) -> float:
    output = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return float(output)
