STATUS: IN PROGRESS

# Issue #22 - Flashcard management and review settings

## 2026-06-25 Ralph iteration 1

Completed the first backend public API behavior increment for review settings:
changing daily review preferences through `PUT /api/settings/review` now
constrains the public `GET /api/flashcards/due` query.

## What Changed

- Added review settings schemas for desired retention, daily new limit, and
  daily review limit.
- Added `GET /api/settings/review`, returning defaults before first save.
- Added `PUT /api/settings/review`, persisting review settings in the existing
  settings KV table.
- Updated `GET /api/flashcards/due` to split due cards into new and review
  buckets, then apply `daily_new_limit` and `daily_review_limit`.
- Kept default settings aligned with the Phase 1 PRD: desired retention `0.9`,
  daily new limit `20`, and daily review limit `200`.

## Verification

- RED: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - Failed as expected with `PUT /api/settings/review` returning `404 Not Found`.
- GREEN: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - `9 passed, 7 warnings`
- Related backend: `uv run pytest backend/tests/test_flashcards_api.py backend/tests/test_settings_api.py backend/tests/test_settings_store.py -q`
  - `25 passed, 7 warnings`
- Full backend: `uv run pytest backend -q`
  - `209 passed, 7 warnings`
- Diff hygiene: `git diff --check`
  - Passed

## Remaining Acceptance Items

- Desired retention setting should influence scheduling behavior, not just be
  persisted.
- Forecast should cover the next 7 days at a basic count level.
- Flashcard management UI still needs edit/settings/forecast controls.

## 2026-06-25 Ralph iteration 2

Completed first local management-flow increment for #22:
added `PUT /api/flashcards/{id}` to edit flashcard `front` and/or `back`,
returning the persisted card and rejecting empty edits.

### What Changed

- Added `FlashcardUpdate` request schema with optional `front` and `back`.
- Added backend route `PUT /api/flashcards/{flashcard_id}`:
  - 404 if card not found
  - 400 if neither `front` nor `back` is provided
  - persists provided fields and returns `FlashcardOut`
- Added flashcard content edit behavior test coverage in
  `backend/tests/test_flashcards_api.py`.

### Verification

- `uv run pytest backend/tests/test_flashcards_api.py -q`
  - `10 passed, 7 warnings`
- `git diff --check`
  - Passed

## Blockers

- No blocker for the next local #22 increment.
