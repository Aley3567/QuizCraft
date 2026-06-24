STATUS: IN PROGRESS

# Issue #20 - Flashcards from concepts and wrong answers

## 2026-06-24 Ralph iteration 2

Completed the next behavior increment for concept-based flashcards:
`POST /api/flashcards/from-concepts` creates normal-priority, source-linked
cards from extracted concepts and is idempotent for repeated concept requests.

## What changed

- Added a public concept flashcard creation request schema.
- Added `POST /api/flashcards/from-concepts`, accepting `concept_ids` and
  returning the created or existing cards in request order.
- Concept cards use the concept name as the front, concept description plus
  source text as the back, `origin=concept`, and `priority=normal`.
- Repeated creation for the same concept returns the existing concept card
  instead of inserting duplicates.
- Added a public API behavior test covering concept creation, source citation
  metadata, normal priority, and duplicate prevention through list verification.

## Verification

- RED: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - Failed as expected with `POST /api/flashcards/from-concepts` returning 404.
- GREEN: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - `2 passed, 7 warnings`
- Related: `uv run pytest backend/tests/test_answer_api.py backend/tests/test_flashcards_api.py -q`
  - `23 passed, 7 warnings`
- Full backend: `uv run pytest backend`
  - `202 passed, 7 warnings`
- Diff hygiene: `git diff --check`
  - Passed

## Remaining acceptance items

- Wrong-answer flashcards for short-answer/fill-blank need explicit behavior
  coverage beyond the generic creation logic.
- Flashcard list UI is not implemented yet.
- FSRS scheduling, due-card review sessions, Anki export, and full management
  flows remain out of scope for #20 or later dependent issues.

## Blockers

- None for the next local increment. Existing project-level real LLM and
  production migration blockers still apply.

## 2026-06-24 Ralph iteration 1

Completed first behavior increment for the issue body's suggested first step:
after a wrong answer is submitted, the public flashcard API can list a
source-linked, elevated-priority card for that wrong answer.

## What changed

- Added `Flashcard` ORM model with `origin`, `priority`, `source_span`,
  `concept_id`, `source_answer_id`, and `source_question_id`.
- Added `GET /api/flashcards` with optional `document_id` and `concept_id`
  filters.
- Updated `POST /api/quiz-sessions/{id}/answer` to create one elevated
  wrong-answer flashcard after an incorrect or partial answer.
- Added a public API behavior test covering wrong-answer submission followed
  by document-scoped and concept-scoped flashcard listing.

## Verification

- RED: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - Failed as expected with `GET /api/flashcards?...` returning 404.
- GREEN: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - `1 passed, 7 warnings`
- Related: `uv run pytest backend/tests/test_answer_api.py backend/tests/test_flashcards_api.py -q`
  - `22 passed, 7 warnings`
- Full backend: `uv run pytest backend`
  - `201 passed, 7 warnings`

## Remaining acceptance items

- Wrong-answer flashcards for short-answer/fill-blank need explicit behavior
  coverage beyond the generic creation logic.
- Flashcard list UI is not implemented yet.
- FSRS scheduling, due-card review sessions, Anki export, and full management
  flows remain out of scope for #20 or later dependent issues.

## Blockers

- None for the next local increment. Existing project-level real LLM and
  production migration blockers still apply.
