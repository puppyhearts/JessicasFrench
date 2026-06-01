# Final Catalog Audit

Generated on May 31, 2026 with:

```bash
npm run build-catalog
```

## Inventory

| Measure | Raw files | Unique after SHA-256 deduplication |
| --- | ---: | ---: |
| PDF documents | 9 | 8 |
| MP3 audio files | 526 | 507 |

The duplicate PDF and nineteen duplicate MP3 files are the repeated TV5Monde bundle. The builder retains canonical paths and aliases rather than duplicating media records.

## Normalized Records

| Collection | Indexed question records | Publishable now |
| --- | ---: | ---: |
| ABC TCF | 70 | 70 |
| Boursin J.-L. | 104 | 6 |
| TCF Entraînement Intensif | 77 | 12 |
| Guide officiel d'entraînement au TCF | 58 | 0 |
| Réussir le TCF | 110 | 104 |
| TCF 250 Activités | 88 | 0 |
| TV5Monde Entraînement | 40 | 23 |
| **Total** | **547** | **215** |

There are 42 publishable records in the default `Q20-Q39` view: 31 ABC TCF records across its two exercises, two Réussir records, and nine TV5Monde records.

## Extracted Content

- ABC TCF: all 40 oral-comprehension and 30 mock-test correction keys were transcribed from the supplied correction PDF. The answer choices are spoken in the MP3 files, so the UI displays `Proposition A` through `D`.
- Réussir le TCF: all answer keys for `A1` through `C2` were transcribed from the supplied corrections. Six level-introduction tracks are indexed but are not questions.
- TCF Entraînement Intensif: the French OCR adapter publishes the twelve records whose four printed choices and correction key parse cleanly.
- Boursin J.-L.: French OCR is available, but only six manually reviewed records are published. Other scan-derived text remains hidden because the OCR is visibly damaged.
- TV5Monde: the original selectable-text adapter remains active for 23 records.

## Unresolved Content

Incomplete records remain in `content/generated/reports/unresolved.json` and are excluded from normal question browsing.

| Validation issue | Count | Meaning |
| --- | ---: | --- |
| `missing_prompt` | 308 | Prompt extraction or manual review is still required. |
| `missing_choices` | 311 | Four answer choices were not parsed safely. |
| `missing_answer` | 301 | A correction key is still required. |
| `missing_audio` | 25 | No question-level audio is mapped. This includes TV5 grammar and reading items. |
| `needs_audio_split` | 48 | One MP3 covers multiple questions and still needs timestamp splitting. |
| `needs_audio_alignment` | 15 | A TV5 full-series MP3 needs listening-question alignment. |
| `needs_pdf_alignment` | 58 | Official-guide sequential tracks require manual PDF exercise alignment before publication. |
| `unmapped_audio` | 24 | Instruction and retained source tracks are indexed but not connected to questions. |

The supplied TCF 250 PDF is a corrections companion rather than the prompt workbook, so its 88 audio exercises cannot be turned into reliable answerable cards from the supplied files alone. The official guide uses sequential track names across mini-tests, discovery exercises, and training sections; those mappings remain unresolved to avoid false question pairings.

## Functional Audit

Implemented:

- One-time local catalog rebuild with temporary-directory replacement.
- Recursive source scan, SHA-256 deduplication, PDF page counts, and MP3 durations.
- French OCR cache generation via `scripts/ocr-pdf.sh`.
- Public catalog API that filters incomplete questions by default.
- Dark three-column practice page following the supplied references.
- Default `Q20-Q39` filter, collection filter, section filter, direct question navigation, audio speed controls, and range stopping when timestamps exist.
- Correct-answer feedback: green for correct, red for wrong, and green reveal of the correct choice.

Still required for a fully populated website:

- Manual correction of damaged Boursin and Intensif OCR records.
- Manual PDF-to-track alignment for the official guide.
- Add the missing TCF 250 prompt workbook if that package should be published.
- Split shared MP3 files and align full-series TV5 listening audio.
- Generate transcripts with timestamped speech-to-text output.

## Machine-Readable Reports

- `content/generated/manifest.json`
- `content/generated/reports/inventory.json`
- `content/generated/reports/unresolved.json`
