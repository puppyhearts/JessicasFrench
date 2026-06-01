from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OCR_ROOT = ROOT / ".ocr-cache"


@dataclass
class ExtractedQuestion:
    number: int
    prompt: str
    choices: list[tuple[str, str]]
    correct_answer: str | None
    source_page: int


def normalize_ocr(text: str) -> str:
    text = re.sub(r"téléversé par:\s*https?\s*//www\.tcfca\.com", "", text, flags=re.I)
    text = re.sub(r"www\.?tcfca\.com", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def ocr_pages(slug: str) -> list[tuple[int, str]]:
    pages: list[tuple[int, str]] = []
    for path in sorted((OCR_ROOT / slug / "images").glob("page-*.txt")):
        match = re.search(r"page-(\d+)", path.stem)
        if match:
            pages.append((int(match.group(1)), path.read_text(encoding="utf-8", errors="ignore")))
    return pages


def _choices(block: str) -> list[tuple[str, str]]:
    matches = list(
        re.finditer(
            r"(?im)(?:^|\n)\s*(?:(?:C[1I)])|[OQUJLIN|().\[\]_01 ]){0,8}([ABCD8À])(?:\s*[.):]\s*|\s+)",
            block,
        )
    )
    choices: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        raw_value = re.split(
            r"\n\s*(?:SITUATION|QUESTION|NIVEAU|Partie)\b",
            block[match.end():end],
            maxsplit=1,
            flags=re.I,
        )[0]
        value = normalize_ocr(raw_value)
        label = {"8": "B", "À": "A"}.get(match.group(1).upper(), match.group(1).upper())
        if value and label not in {existing_label for existing_label, _ in choices}:
            choices.append((label, value))
    return choices


def _numbered_choices(text: str) -> dict[int, list[tuple[str, str]]]:
    markers = list(re.finditer(r"(?m)^\s*(\d{1,2})\.\s*", text))
    extracted: dict[int, list[tuple[str, str]]] = {}
    for index, marker in enumerate(markers):
        number = int(marker.group(1))
        block = text[marker.end():markers[index + 1].start() if index + 1 < len(markers) else len(text)]
        choices = _choices(block)
        if len(choices) == 4:
            extracted[number] = choices
    return extracted


INTENSIF_ANSWERS = {
    "training": {
        1: "A", 2: "B", 3: "A", 5: "C", 6: "A", 7: "D", 8: "B", 9: "A", 10: "A",
        12: "B", 13: "B", 14: "A", 16: "A", 17: "D", 20: "C", 26: "D", 27: "D",
        30: "A", 31: "A", 36: "C",
    },
    "test1": {
        1: "A", 3: "D", 4: "B", 6: "B", 7: "A", 8: "C", 10: "A", 11: "D",
        14: "D", 15: "B",
    },
    "test2": {
        3: "A", 4: "B", 6: "D", 7: "A", 8: "B", 9: "C", 10: "D", 11: "D",
        12: "B", 14: "C", 15: "D",
    },
}

ABC_ANSWERS = {
    "Compréhension orale": {
        1: "A", 2: "C", 3: "C", 4: "C", 5: "C", 6: "C", 7: "D", 8: "D", 9: "C",
        10: "B", 11: "B", 12: "B", 13: "B", 14: "A", 15: "D", 16: "B", 17: "B",
        18: "D", 19: "D", 20: "A", 21: "D", 22: "D", 23: "D", 24: "B", 25: "A",
        26: "B", 27: "D", 28: "A", 29: "C", 30: "B", 31: "A", 32: "D", 33: "B",
        34: "C", 35: "A", 36: "B", 37: "C", 38: "B", 39: "D", 40: "B",
    },
    "Test blanc": {
        1: "D", 2: "D", 3: "B", 4: "D", 5: "A", 6: "D", 7: "A", 8: "B", 9: "D",
        10: "C", 11: "A", 12: "B", 13: "A", 14: "A", 15: "D", 16: "B", 17: "D",
        18: "A", 19: "D", 20: "C", 21: "C", 22: "C", 23: "B", 24: "D", 25: "B",
        26: "A", 27: "A", 28: "B", 29: "B", 30: "B",
    },
}

TV5_ANSWERS = {
    1: {
        1: "C", 2: "D", 3: "B", 4: "A", 5: "D", 6: "B", 7: "D", 8: "A", 9: "A", 10: "C",
        11: "D", 12: "D", 13: "B", 14: "B", 15: "D", 16: "A", 17: "C", 18: "C", 19: "D", 20: "D",
        21: "D", 22: "A", 23: "C", 24: "C", 25: "B", 26: "B", 27: "B", 28: "D", 29: "C", 30: "D",
        31: "D", 32: "B", 33: "C", 34: "C", 35: "A", 36: "C", 37: "C", 38: "A", 39: "A", 40: "A",
    },
}

# These OCR-derived records were reviewed after extraction. Other Boursin
# records remain indexed but unpublished until their scan text is corrected.
BOURSIN_VERIFIED_KEYS = {
    (1, 1), (1, 5), (2, 3), (2, 4), (2, 5), (3, 13),
}

REUSSIR_ANSWERS = {
    "A1": {
        1: "C", 2: "B", 3: "C", 4: "D", 5: "B", 6: "A", 7: "C", 8: "A", 9: "A",
        10: "B", 11: "B", 12: "D", 13: "A", 14: "A", 15: "C", 16: "C",
    },
    "A2": {
        1: "D", 2: "B", 3: "C", 4: "A", 5: "C", 6: "B", 7: "C", 8: "B", 9: "B",
        10: "D", 11: "A", 12: "C", 13: "A", 14: "B", 15: "A", 16: "C",
    },
    "B1": {
        1: "C", 2: "B", 3: "D", 4: "B", 5: "D", 6: "C", 7: "B", 8: "B", 9: "C",
        10: "B", 11: "B", 12: "A", 13: "C", 14: "C", 15: "B", 16: "B", 17: "A",
        18: "D", 19: "D", 20: "C",
    },
    "B2": {
        1: "B", 2: "C", 3: "B", 4: "C", 5: "D", 6: "B", 7: "B", 8: "A", 9: "B",
        10: "A", 11: "D", 12: "C", 13: "A", 14: "B", 15: "D", 16: "B", 17: "C",
        18: "B", 19: "A", 20: "B",
    },
    "C1": {
        1: "A", 2: "B", 3: "A", 4: "C", 5: "D", 6: "A", 7: "C", 8: "C", 9: "C",
        10: "C", 11: "A", 12: "D", 13: "B", 14: "B", 15: "B", 16: "A",
    },
    "C2": {
        1: "B", 2: "D", 3: "A", 4: "B", 5: "C", 6: "B", 7: "B", 8: "B", 9: "B",
        10: "C", 11: "D", 12: "A", 13: "B", 14: "B", 15: "B", 16: "D",
    },
}


def spoken_choices() -> list[tuple[str, str]]:
    return [(label, f"Proposition {label}") for label in "ABCD"]


def extract_intensif_choices(group: str, printed_page: int, number: int) -> tuple[list[tuple[str, str]] | None, int | None]:
    offset = -2 if group == "training" else -6 if group == "test1" else -8
    expected = printed_page + offset
    pages = dict(ocr_pages("intensif"))
    for page in (expected, expected - 1, expected + 1):
        choices = _numbered_choices(pages.get(page, "")).get(number)
        if choices:
            return choices, page
    return None, None


@lru_cache(maxsize=1)
def extract_boursin() -> dict[tuple[int, int], ExtractedQuestion]:
    extracted: dict[tuple[int, int], ExtractedQuestion] = {}
    answers: dict[tuple[int, int], str] = {}
    level = 0
    for page, raw_text in ocr_pages("boursin"):
        for level_match in re.finditer(r"(?i)NIVEAU\s*([1-6])", raw_text):
            level = int(level_match.group(1))
        markers = list(re.finditer(r"(?i)SITUATION\s*N[°ºo]?\s*(\d+)", raw_text))
        for index, marker in enumerate(markers):
            number = int(marker.group(1))
            block = raw_text[marker.end():markers[index + 1].start() if index + 1 < len(markers) else len(raw_text)]
            answer_match = re.search(r"(?i)R[ée]ponse\s*:?\s*([ABCD])(?:\b|\.)", block)
            choices = _choices(block)
            key = (level, number)
            if level and answer_match:
                answers[key] = answer_match.group(1).upper()
            if level and len(choices) == 4:
                extracted[key] = ExtractedQuestion(
                    number=number,
                    prompt=f"Écoutez l'enregistrement puis choisissez la bonne réponse.",
                    choices=choices,
                    correct_answer=None,
                    source_page=page,
                )
    for key, answer in answers.items():
        if key in extracted:
            extracted[key].correct_answer = answer
    return extracted
