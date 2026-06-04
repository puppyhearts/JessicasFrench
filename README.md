# Jessica's French Audio Practice

A focused French listening-practice app for TCF-style study. It turns a large collection of French audio questions, transcripts, answer keys, and source images into a fast browser-based practice tool with instant feedback.

Live site: https://puppyhearts.github.io/JessicasFrench/

## Why This Exists

French listening practice is often scattered across PDFs, audio folders, correction sheets, and transcripts. This project pulls those pieces into one study interface:

- listen to authentic TCF-style audio,
- read the French transcript while studying,
- choose from A-D answer options,
- get immediate right/wrong feedback,
- track your score as you work,
- jump between questions by difficulty and test source,
- practice from a static GitHub Pages site without running a backend.

The current public catalog contains **1,920 reviewed questions**, including **1,765 listening questions**, plus grammar and reading cards from the imported source material.

## Demo Highlights

The practice page is organized as a three-panel workspace:

| Area | What it helps with |
| --- | --- |
| Left panel | French transcript for the current audio, with support for timed word highlighting when available. |
| Center panel | Source reference, audio controls, prompt, images when relevant, and the answer choices. |
| Right panel | Source tabs, section filters, score, reset button, and a scrollable question navigator grouped by difficulty. |

Recommended screenshots to add:

```text
docs/screenshots/practice-listening.png  # transcript + audio + answer choices
docs/screenshots/tcf-files-tab.png       # new TCF Files source tab
docs/screenshots/feedback-state.png      # green/red answer feedback
```

## How To Study With It

1. Open the live site.
2. Choose a source tab:
   - **Catalog**: curated material from ABC TCF, Réussir le TCF, TV5Monde, and other sources.
   - **TCF Files**: the large imported listening bank with 1,560 audio questions.
3. Choose a section:
   - **CO** for listening practice,
   - **Grammar** for structure questions,
   - **Reading** for PDF-backed reading cards.
4. Press play, listen carefully, and select A, B, C, or D.
5. Review the feedback:
   - correct choices turn green,
   - wrong selections turn red,
   - the correct answer is revealed in green.
6. Use the right-hand question grid to continue through a difficulty block.
7. Use **Reset** when you want a fresh score.

Study suggestion: first answer without reading the transcript, then replay the audio while checking the transcript. This gives you both exam-style practice and targeted listening review.

## Current Content

| Source | Published questions |
| --- | ---: |
| TCF Files | 1,560 |
| ABC TCF | 200 |
| Réussir le TCF | 104 |
| TV5Monde Entraînement | 38 |
| TCF Entraînement Intensif | 12 |
| Boursin J.-L. | 6 |
| Guide officiel / TCF 250 | indexed but not published yet |

Audio is hosted through GitHub Releases:

- `audio-v2`: first 1,000 hashed audio files,
- `audio-v3`: 392 fallback audio files.

The static site automatically tries the fallback release when an audio file is not in the primary release.

## Features

- Static GitHub Pages deployment.
- 1,920 answerable questions in the committed static catalog.
- MP3 and OGG playback.
- GitHub Release audio hosting.
- Persistent local scoring with `localStorage`.
- Source tabs to separate the main catalog from the imported TCF Files bank.
- Difficulty-ranked question groups in blocks of twenty.
- PDF/WebP image support for visual and reading questions.
- FastAPI backend for local development and direct media serving.
- SQLite catalog generated from local source files.

## What Lives In Git

| Path | In git? | Notes |
| --- | --- | --- |
| `apps/web/` | yes | Next.js app and static catalog files. |
| `apps/web/public/catalog/` | yes | Published `questions.json`, `collections.json`, images, and transcript exports. |
| `Sources/` | no | Large local PDFs, audio, extracted archives, and raw source data. |
| `audio-release/` | no | Generated release-upload folder. |
| `content/generated/` | no | Rebuilt SQLite catalog and reports. |
| `.ocr-cache/` | no | Local OCR cache for scanned PDFs. |
| `.transcript-cache/` | no | Local speech-to-text cache. |

## Local Development

With Docker:

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:3000
```

Without Docker, install dependencies and run the web app from `apps/web` as usual.

## Rebuilding The Catalog

Place source PDFs and audio files in `Sources/` first. These files are intentionally ignored by git.

```bash
python3 -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt
npm run prepare-ocr-caches
npm run build-catalog
```

Then apply reviewed corrections and export the static catalog:

```bash
.venv/bin/python scripts/patch-abc-choices.py
.venv/bin/python scripts/patch-reussir-choices.py
.venv/bin/python scripts/patch-choices-corrections.py
npm run export-static-catalog
```

## Updating Hosted Audio

Audio files are too large for git. Prepare release assets with:

```bash
python scripts/prepare-audio-release.py --out-dir audio-release
```

The script writes files as:

```text
audio-release/{sha256}.{extension}
```

Upload them to GitHub Releases and set repository variables:

```text
AUDIO_BASE_URL=https://github.com/OWNER/REPO/releases/download/audio-v2
AUDIO_FALLBACK_BASE_URLS=https://github.com/OWNER/REPO/releases/download/audio-v3
```

Use multiple releases when the asset count exceeds GitHub's release limit.

## Deployment

The GitHub Pages workflow builds the committed static catalog on every push to `main`.

Workflow:

1. install web dependencies,
2. set the Pages base path,
3. build the static Next.js app,
4. deploy `apps/web/out` to GitHub Pages.

The workflow reads `AUDIO_BASE_URL` and `AUDIO_FALLBACK_BASE_URLS` from repository variables.

## Verification

Run these before pushing changes:

```bash
npm run test:parser
npm --prefix apps/web run build
git diff --check
```

For the detailed catalog boundary, see:

- [Final Catalog Audit](docs/FINAL_CATALOG_AUDIT.md)
- [Practice UI Requirements](docs/PRACTICE_UI_REQUIREMENTS.md)
