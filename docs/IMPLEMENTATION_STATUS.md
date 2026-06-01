# Implementation Status

## Runnable today

- One-time `npm run build-catalog` command that scans all seven supplied source packages and atomically replaces the local generated catalog.
- SHA-256 deduplication for the repeated TV5Monde bundle.
- Filename-based indexing for 547 normalized records across 507 unique MP3 files.
- Generated SQLite catalog API used by the normal practice frontend.
- Docker Compose foundation for Next.js, FastAPI and PostgreSQL with pgvector.
- Local SQLite fallback for development without Docker.
- Recursive source scanning for PDFs and `Entrainement - XX.mp3` audio files.
- TV5Monde series detection with selectable-text extraction and Tesseract OCR fallback.
- Question, answer-choice and native correction-grid extraction for the first TV5Monde layout.
- French OCR cache generation for scan-heavy PDFs.
- Complete correction-key mappings for ABC TCF listening and Réussir le TCF levels `A1` through `C2`.
- Reviewed OCR publication gates for Boursin and TCF Entraînement Intensif.
- Idempotent persistence: repeated imports update existing records without duplication.
- Provisional listening ranges derived from silence analysis.
- Public API filtering so incomplete parser output is not published.
- Dark practice UI with section navigation, series selection, answer feedback, audio ranges and speed controls.
- Admin page with ingestion run summaries.

See [FINAL_CATALOG_AUDIT.md](FINAL_CATALOG_AUDIT.md) for exact publishable and unresolved counts. See [PRACTICE_UI_REQUIREMENTS.md](PRACTICE_UI_REQUIREMENTS.md) for the retained reference-image layout contract.

## Required before production

- Refine all TV5Monde layout adapters and raster correction-grid recognition for series 2-19.
- Add extracted reading-question images and image crops.
- Run faster-whisper `large-v3`, align the fifteen listening segments per series and generate transcript JSON, SRT and VTT artifacts.
- Add synchronized transcript highlighting and vocabulary popups.
- Add OpenAI metadata generation, answer explanations and pgvector embeddings.
- Add semantic search, flashcards with SM-2, progress dashboard and mock exam mode.
- Add authentication and per-user study history.
- Move ingestion API execution into a background worker with progress events.
- Add Google Cloud Storage provider behind the local storage interface.
- Add end-to-end tests and a completed full-OCR ingestion regression run.

## Verification notes

- `--text-only` development import currently detects 13 series headings, all 19 audio tracks, 40 series-1 questions and 23 publishable series-1 questions.
- The generated catalog currently exposes 215 reviewed records; 42 are available in the default `Q20-Q39` view.
- Full `npm run ingest` enables OCR fallback and is intentionally slower on the supplied 530-page PDF.
- `npm audit --omit=dev` reports a moderate transitive PostCSS advisory through Next.js 15.5.18. npm does not currently offer a sensible patched Next.js 15 resolution.
