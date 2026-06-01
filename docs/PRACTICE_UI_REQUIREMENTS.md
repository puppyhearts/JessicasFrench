# Practice UI Requirements

This file retains the requested practice-page behavior derived from the supplied reference images.

## Layout

The default desktop page is a three-column workspace:

| Region | Required content |
| --- | --- |
| Left | Transcript for the current audio question. If transcription is not available yet, show that state explicitly. |
| Top middle | Every known occurrence of the current question, including website, test or book grouping, and source question number. Example: `Formation TCF · Test 13 · Question 27`. |
| Middle | Instructions, prompt, audio controls when applicable, and answer options. |
| Right | Available questions with direct navigation. Keep this panel independently scrollable and group questions by difficulty rank in blocks of twenty. Show the running score instead of `Toutes` or `Q20-Q39` tabs. |

The visual direction is the dark navy and purple interface shown in the reference images: bordered rounded panels, a purple active-question state, compact question grid, and a distinct reference card above the answer card.

## Answer Feedback

Answer submission is immediate:

- A correct selected option becomes green.
- An incorrect selected option becomes red.
- When the selected option is incorrect, the correct option also becomes green.
- The selected question remains visible so the user can review the result.
- Question-bubble results and the running score persist locally until the Reset button is used.

## Catalog Behavior

- The frontend reads normalized records from `content/generated/catalog.sqlite` through FastAPI.
- It never parses a PDF or runs OCR during a browser request.
- Incomplete or ambiguous source records remain in the catalog audit but do not appear as answerable questions.
- The reference panel supports multiple occurrences for a canonical question. Cross-package deduplication must not be guessed when OCR text is missing.

## Current Implementation

The requested interaction is implemented in `apps/web/app/page.tsx`. Timed transcript highlighting is supported when generated transcript words exist. Remaining transcript generation and cross-package question matching are data-processing work, not missing browser controls.
