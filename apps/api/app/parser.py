from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SERIES_RE = re.compile(r"(?:S[ée]rie(?: d.?entra[îi]nement)?|Entra[îi]nement)\s*(?:n[°o]?)?\s*(\d+)", re.I)
QUESTION_RE = re.compile(r"(?m)^\s*(\d{1,2})(?:\.\s+|\s*\n)")
CHOICE_RE = re.compile(r"(?m)^\s*([ABCD])(?:\s+|\t+)(.+?)(?=^\s*[ABCD](?:\s+|\t+)|\Z)", re.S)
ANSWER_GROUP_RE = re.compile(r"(\d{1,2})\s+([□\uf078])\s+([□\uf078])\s+([□\uf078])\s+([□\uf078])")
INSTRUCTION_MARKERS = ("Écoutez", "Choisissez", "Lisez")


@dataclass
class ParsedChoice:
    label: str
    text: str


@dataclass
class ParsedQuestion:
    number: int
    section: str
    prompt: str
    instructions: str
    page_number: int
    choices: list[ParsedChoice] = field(default_factory=list)
    correct_answer: str | None = None
    confidence: float = 0.0


@dataclass
class ParsedSeries:
    number: int
    start_page: int
    end_page: int
    questions: list[ParsedQuestion] = field(default_factory=list)


def run(*args: str) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout


@lru_cache(maxsize=1)
def tesseract_language_args() -> tuple[str, ...]:
    languages = run("tesseract", "--list-langs")
    return ("-l", "fra") if re.search(r"(?m)^fra$", languages) else ()


def page_count(pdf: Path) -> int:
    info = run("pdfinfo", str(pdf))
    match = re.search(r"^Pages:\s+(\d+)", info, re.M)
    if not match:
        raise ValueError(f"Unable to read PDF page count: {pdf}")
    return int(match.group(1))


@lru_cache(maxsize=4)
def extract_document_pages(pdf: Path) -> tuple[str, ...]:
    text = run("pdftotext", "-layout", str(pdf), "-")
    return tuple(text.split("\f"))


def extract_page_text(pdf: Path, page: int, ocr_fallback: bool = False) -> str:
    pages = extract_document_pages(pdf)
    text = pages[page - 1] if page <= len(pages) else ""
    if ocr_fallback and len(normalize(text)) < 80:
        cached = ROOT / ".ocr-cache" / "tv5monde" / "images" / f"page-{page:03d}.txt"
        if cached.exists():
            return cached.read_text(encoding="utf-8", errors="ignore")
        return extract_page_ocr(pdf, page)
    return text


@lru_cache(maxsize=1024)
def extract_page_ocr(pdf: Path, page: int) -> str:
    with tempfile.TemporaryDirectory(prefix="tcf-page-") as directory:
        prefix = Path(directory) / "page"
        subprocess.run(
            ["pdftoppm", "-f", str(page), "-l", str(page), "-r", "180", "-png", "-singlefile", str(pdf), str(prefix)],
            check=True,
            capture_output=True,
        )
        image = str(prefix.with_suffix(".png"))
        return run("tesseract", image, "stdout", *tesseract_language_args())


def section_for(question_number: int) -> str:
    if question_number <= 15:
        return "listening"
    if question_number <= 25:
        return "grammar"
    return "reading"


def normalize(text: str) -> str:
    text = re.sub(r"téléversé par:\s*https?://www\.tcfca\.com", "", text, flags=re.I)
    text = re.sub(r"www?\.?tcfca\.com", "", text, flags=re.I)
    text = re.sub(r"(?:\bom\b|\ba\.\s*c\b|\.tc\b|\bfc\b|(?:^|\s)w{1,3}(?=\s|$))", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_questions_from_page(text: str, page: int) -> list[ParsedQuestion]:
    matches = list(QUESTION_RE.finditer(text))
    parsed: list[ParsedQuestion] = []
    for index, match in enumerate(matches):
        number = int(match.group(1))
        if not 1 <= number <= 40:
            continue
        block = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        block = re.split(r"(?:Entra[îi]nement au TCF|CIEP\s*[–/-]\s*TV5MONDE)", block, maxsplit=1)[0]
        choice_matches = list(CHOICE_RE.finditer(block))
        choices = [ParsedChoice(item.group(1), normalize(item.group(2))) for item in choice_matches]
        first_choice = choice_matches[0].start() if choice_matches else len(block)
        lines = [normalize(line) for line in block[:first_choice].splitlines()]
        lines = [line for line in lines if line]
        instruction_lines = [line for line in lines if line.startswith(INSTRUCTION_MARKERS)]
        prompt_lines = [line for line in lines if line not in instruction_lines]
        prompt = normalize(" ".join(prompt_lines))
        prompt = re.sub(r"^(?:réponse et cochez la bonne réponse\.|la bonne réponse\.|bonne réponse\.)\s*", "", prompt, flags=re.I)
        confidence = 0.95 if len(choices) == 4 else 0.55 if choices else 0.25
        parsed.append(
            ParsedQuestion(
                number=number,
                section=section_for(number),
                prompt=prompt or f"Question {number}",
                instructions=normalize(" ".join(instruction_lines)),
                page_number=page,
                choices=choices,
                confidence=confidence,
            )
        )
    return parsed


def parse_answer_key(text: str) -> dict[int, str]:
    if "Corrig" not in text:
        return {}
    answers: dict[int, str] = {}
    offset = 0
    for line in text.splitlines():
        if "Première partie" in line:
            offset = 0
        elif "Deuxième partie" in line:
            offset = 15
        elif "Troisième partie" in line:
            offset = 25
        for match in ANSWER_GROUP_RE.finditer(line):
            number = int(match.group(1))
            marks = match.groups()[1:]
            checked = [index for index, mark in enumerate(marks) if mark == "\uf078"]
            if len(checked) == 1:
                global_number = number + offset if offset and number <= 15 else number
                answers[global_number] = "ABCD"[checked[0]]
    return answers


def detect_series_pages(pdf: Path, ocr_fallback: bool = True) -> list[ParsedSeries]:
    total = page_count(pdf)
    starts: dict[int, int] = {}
    current: int | None = None
    for page in range(1, total + 1):
        text = extract_page_text(pdf, page, ocr_fallback=ocr_fallback)
        match = SERIES_RE.search(text)
        if match:
            candidate = int(match.group(1))
            if 1 <= candidate <= 99:
                current = candidate
                starts.setdefault(current, page)
        if current is None and page == 3:
            current = 1
            starts[1] = page
    ordered = sorted(starts.items(), key=lambda item: item[1])
    return [
        ParsedSeries(number=number, start_page=start, end_page=(ordered[index + 1][1] - 1 if index + 1 < len(ordered) else total))
        for index, (number, start) in enumerate(ordered)
    ]


def parse_pdf(pdf: Path, ocr_fallback: bool = True) -> list[ParsedSeries]:
    series = detect_series_pages(pdf, ocr_fallback=ocr_fallback)
    for item in series:
        found: dict[int, ParsedQuestion] = {}
        answers: dict[int, str] = {}
        for page in range(item.start_page, item.end_page + 1):
            text = extract_page_text(pdf, page, ocr_fallback=ocr_fallback)
            answers.update(parse_answer_key(text))
            for question in parse_questions_from_page(text, page):
                previous = found.get(question.number)
                if previous is None or question.confidence > previous.confidence:
                    found[question.number] = question
        for number, answer in answers.items():
            if number in found:
                found[number].correct_answer = answer
        item.questions = [found[number] for number in sorted(found)]
    return series
