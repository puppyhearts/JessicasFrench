# One-Time Source Ingestion Plan

## Objective

Build the local study catalog once from `Sources/`, validate it, and serve the generated catalog and assets through FastAPI. Runtime ingestion is not required for normal use.

The generated catalog should be reproducible, but the frontend must only read normalized local artifacts. It must never parse PDFs, inspect source filenames, run OCR, or invoke Whisper during a request.

## Inventory

The current source tree contains:

| Measure | Raw | Unique after hashing |
| --- | ---: | ---: |
| PDFs | 9 | 8 |
| Audio files | 526 | 507 |

The two TV5 folders are byte-for-byte duplicates. Ingest one canonical TV5 bundle and retain both paths as aliases.

| Canonical package | PDFs | Unique audio | Duration | Mapping characteristics |
| --- | ---: | ---: | ---: | --- |
| TV5Monde Entraînement | 1 | 19 | 4h 35m | One full-series MP3 per training series; split into listening-question ranges |
| ABC TCF | 2 | 66 | 54m | Main workbook plus corrections PDF; direct question clips with four multi-question clips and 30 mock-test clips |
| Boursin J.-L. | 1 | 110 | 3h 51m | Six instruction clips and 104 item clips grouped by levels 1-6 |
| Guide officiel d'entraînement au TCF | 1 | 58 | 46m | Sequential audio tracks; text-rich PDF with explicit transcript and correction sections |
| Réussir le TCF | 1 | 89 | 1h 42m | CEFR-coded clips; some clips cover question ranges; two `.sfk` editor sidecars must be ignored |
| TCF 250 Activités | 1 | 88 | 54m | Correction companion plus audio for exercises 1-58 and 171-200 |
| TCF Entraînement Intensif | 1 | 77 | 49m | Filenames encode part, CEFR level, PDF page, and exercise ID |

The unique audio library is approximately 13h 31m.

## Generated Artifact Layout

Use SQLite and immutable files:

```text
content/generated/
├── catalog.sqlite
├── manifest.json
├── reports/
│   ├── inventory.json
│   ├── validation.json
│   └── unresolved.json
├── audio/
│   ├── originals/<sha256>.mp3
│   └── clips/<question-id>.mp3
├── images/
│   └── <question-id>/<asset-id>.webp
└── transcripts/
    └── <question-id>/
        ├── transcript.json
        ├── transcript.txt
        ├── transcript.srt
        └── transcript.vtt
```

Use SHA-256 content addressing for original assets. Use hard links where possible to avoid copying large files. Keep normalized question clips only where a source MP3 covers multiple questions.

SQLite is the appropriate runtime store because the website is local-first and ingestion happens once. Keep PostgreSQL migrations available as an optional deployment path, but do not require PostgreSQL for local use.

## Catalog Schema

The generated database should contain:

| Table | Purpose |
| --- | --- |
| `source_packages` | Canonical package records |
| `source_aliases` | Duplicate or alternate source paths |
| `source_documents` | PDF hashes, paths, extraction mode, and page counts |
| `source_pages` | Extracted text, OCR text, page image path, and confidence |
| `audio_assets` | Original MP3 metadata, hashes, and durations |
| `audio_ranges` | Start and end times when an MP3 covers multiple questions |
| `questions` | Canonical question record |
| `question_occurrences` | Package, document, page, exercise number, series, and source labels |
| `answer_choices` | A-D answer text and ordering |
| `correct_answers` | Correct answer and extraction provenance |
| `question_assets` | Extracted images and page crops |
| `transcripts` | Full transcript artifacts |
| `transcript_sentences` | Sentence timestamps |
| `transcript_words` | Word timestamps |
| `vocabulary` | Extracted vocabulary |
| `grammar_concepts` | Extracted grammar concepts |
| `validation_issues` | Unresolved or low-confidence records |

Keep canonical questions separate from occurrences. If the same question appears in multiple books or websites, the frontend should show one question and list every occurrence in the reference panel.

## Extraction Pipeline

Create a separate offline command:

```bash
npm run build-catalog
```

The command should rebuild `content/generated/` from scratch in a temporary directory and atomically replace the previous catalog only after validation passes.

### 1. Inventory and Deduplication

1. Scan all PDFs and MP3s recursively.
2. Ignore `.DS_Store`, `.sfk`, and unsupported files.
3. Compute SHA-256 hashes.
4. Collapse the duplicate TV5 directory into aliases.
5. Store media metadata from `ffprobe`.
6. Write `reports/inventory.json`.

### 2. PDF Normalization

For each unique PDF:

1. Run `pdftotext -layout`.
2. Render each page to a temporary image.
3. Use the native text layer when it is complete.
4. Run French Tesseract OCR for scan-heavy or low-text pages.
5. Remove repeated tcfca.com headers, diagonal watermarks, and advertisement pages.
6. Retain original page numbers and rendered page images for auditability.

Several PDFs are scan-heavy. OCR is part of the normal one-time build, not an exceptional fallback.

### 3. Provider-Specific Adapters

Implement adapters behind one interface:

```python
class SourceAdapter:
    def discover_documents(self): ...
    def parse_questions(self): ...
    def parse_answers(self): ...
    def map_audio(self): ...
    def validate(self): ...
```

#### `Tv5MondeAdapter`

- Ingest one canonical copy of the 530-page PDF and nineteen full-series MP3s.
- Detect series 1-19 despite footer format changes and scanned pages.
- Parse each series into listening, grammar, and reading sections.
- Parse native and raster correction grids.
- Transcribe each full-series MP3.
- Split listening tracks using spoken numbering, Whisper timestamps, and long pauses.
- Store ranges first; export clips only after ranges pass validation.

#### `AbcTcfAdapter`

- Parse the 129-page workbook and the separate 16-page corrections PDF.
- Map `TCF_P##_CO_questionXX.mp3` directly.
- Split the four `questionsXX_YY` MP3s using transcription timestamps.
- Store the 30 `TCFblanc_questionXX.mp3` files as a separate mock exam.

#### `BoursinAdapter`

- Parse the 294-page scan-heavy workbook with OCR.
- Treat six `niveauN-consignes.mp3` files as section instructions.
- Map the remaining 104 `situation` or `enregistrement` clips directly.
- Preserve levels 1-6 as the book's native progression metadata.

#### `OfficialGuideAdapter`

- Prefer the PDF text layer and normalize its imperfect character encoding.
- Use the table of contents to locate discovery, training, transcript, and correction sections.
- Map `AudioTrack 01` through `AudioTrack 58` in order.
- Parse transcript and correction sections before using Whisper; use Whisper for timestamps.

#### `ReussirTcfAdapter`

- OCR the 281-page workbook.
- Map CEFR-coded filenames such as `A1Q01`, `B1Q03-04`, and `C2Q14-15`.
- Ignore the two `.sfk` files.
- Normalize filename typos such as `TCFF` and repeated `TCF`.
- Split range clips with Whisper timestamps.

#### `Tcf250ActivitiesAdapter`

- OCR the 25-page corrections companion.
- Map the 88 audio clips directly to exercises 1-58 and 171-200.
- Do not invent missing exercises 59-170. Mark them as absent from the supplied source set.
- Publish only records that have enough prompt, audio, and correction data for the frontend.

#### `IntensiveTrainingAdapter`

- OCR the 237-page workbook.
- Parse filename metadata directly: part, CEFR level, PDF page, and exercise ID.
- Import `Partie3` listening exercises and the `Partie5` test folders independently.
- Preserve Test 1 and Test 2 as separate collections.

### 4. Audio and Transcript Processing

For each published listening question:

1. Normalize audio metadata with FFmpeg without lossy re-encoding where possible.
2. Use direct MP3 mapping when the filename identifies one question.
3. Split only multi-question or series-level files.
4. Run Whisper `large-v3` once offline.
5. Store text, SRT, VTT, sentence timestamps, and word timestamps.
6. Validate that ranges are ordered, non-overlapping, and within source-track duration.

### 5. Answer Parsing and Validation

Answers must come from supplied correction pages. Do not infer answers with an LLM.

Validation rules:

- Every published question has a stable ID.
- Every published multiple-choice question has exactly four choices unless the source format explicitly differs.
- Every published practice question has one correct answer.
- Every listening question has one audio asset or valid range.
- Every range lies inside its source MP3 duration.
- Every source filename maps to a record or an explicit ignored-file reason.
- Duplicate hashes are represented once.
- Low-confidence OCR records remain in `validation_issues` and are not returned by default.

Write a machine-readable report and a concise Markdown summary. The build should fail if required records are ambiguous.

### 6. Optional AI Enrichment

After the deterministic catalog passes validation:

1. Generate vocabulary, grammar concepts, summaries, CEFR estimates, and topics.
2. Store AI provenance and prompt version.
3. Generate answer explanations only for questions with deterministic correct answers.
4. Store embeddings only if semantic search is needed.

AI metadata is enrichment. It must never determine source mappings or correct answers.

## Frontend Contract

FastAPI should serve only the generated catalog:

```text
GET /api/collections
GET /api/questions?collection=&section=&level=&published=true
GET /api/questions/{id}
GET /api/questions/{id}/transcript
GET /api/audio/{asset_id}
GET /api/images/{asset_id}
```

The question response should include:

```json
{
  "id": "question-id",
  "collection": "abc-tcf",
  "section": "listening",
  "level": "B2",
  "prompt": "...",
  "choices": [{"label": "A", "text": "..."}],
  "correctAnswer": "C",
  "audio": {"assetId": "...", "start": 0, "end": 18.4},
  "occurrences": [
    {"package": "ABC TCF", "page": 42, "exercise": "31"}
  ]
}
```

The current frontend can remain API-driven. Replace runtime ingestion controls with a catalog-status page showing the generated manifest and validation report.

## Implementation Order

1. Replace the current recurring ingestion command with `build-catalog`.
2. Add inventory hashing and canonical source aliases.
3. Create the SQLite catalog schema and artifact writer.
4. Implement adapters in this order:
   - ABC TCF
   - TCF Entraînement Intensif
   - Official Guide
   - Boursin
   - Réussir le TCF
   - TCF 250 Activités
   - TV5Monde
5. Run deterministic validation and resolve adapter failures.
6. Run Whisper once for published listening records.
7. Add optional AI enrichment.
8. Point FastAPI exclusively at `content/generated/catalog.sqlite`.
9. Remove runtime parsing from the normal application path.

This order prioritizes packages with direct per-question filenames before TV5Monde's more expensive series-level alignment work.

