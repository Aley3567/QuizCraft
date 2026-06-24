STATUS: COMPLETE

# Issue #20 - Flashcards from concepts and wrong answers

## 2026-06-24 Ralph iteration 4

Completed the final #20 behavior increment for non-MCQ wrong-answer
flashcards: fill-blank and short-answer responses now have public API coverage
showing that a wrong response creates an elevated, source-linked card, and a
later corrected response removes the stale wrong-answer card from the flashcard
list.

## What changed

- Added a parameterized public API test for fill-blank and short-answer
  correction behavior through `POST /api/quiz-sessions/{id}/answer` and
  `GET /api/flashcards`.
- Kept the test at the public route boundary with mocked LLM responses.
- Updated the answer route so a corrected source `Answer` deletes its existing
  `origin=wrong_answer` flashcard instead of leaving stale review material.

## Verification

- RED: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - Failed as expected: corrected fill-blank and short-answer responses still
    returned the old wrong-answer card from `GET /api/flashcards`.
- GREEN: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - `4 passed, 7 warnings`
- Related: `uv run pytest backend/tests/test_answer_api.py backend/tests/test_flashcards_api.py -q`
  - `25 passed, 7 warnings`
- Full backend: `uv run pytest backend`
  - `204 passed, 7 warnings`
- Style note: `uv run ruff format --check ...` and `uv run ruff check ...`
  could not run because `ruff` is not installed in the project environment
  (`Failed to spawn: ruff`). New test lines were manually scanned for
  `length > 100`.

## Remaining acceptance items

- None for #20. Concept cards, wrong-answer cards, elevated priority,
  document/concept listing, and result-page flashcard display are covered.
- FSRS scheduling, due-card review sessions, Anki export, and full management
  flows remain out of scope for later dependent issues.

## Blockers

- None for #20. Existing project-level real LLM and production migration
  blockers still apply.

## 2026-06-24 Ralph iteration 3

Completed the next visible behavior increment for the flashcard list UI:
after a quiz is finished, the result page reads `GET /api/flashcards` for the
current document and displays source-linked concept cards and wrong-answer cards.

## What changed

- Added the frontend `FlashcardOut` type matching the backend public schema.
- Added `listFlashcards({ documentId, conceptId })` to the frontend API client.
- Added `FlashcardList`, a compact document-scoped list that shows card origin,
  priority, front/back, and source citation.
- Rendered the flashcard list on the quiz result page using the quiz session's
  `document_id`.
- Kept FSRS review, card editing, and management flows out of this increment.

## Verification

- RED: `cd frontend && npm run test`
  - Failed as expected with `listFlashcards is not a function`.
- GREEN: `cd frontend && npm run test`
  - `34 passed`
- Frontend typecheck: `cd frontend && npm run typecheck`
  - Passed
- Backend related: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - `2 passed, 7 warnings`
- Backend related: `uv run pytest backend/tests/test_answer_api.py backend/tests/test_flashcards_api.py -q`
  - `23 passed, 7 warnings`
- Full frontend build: `cd frontend && npm run build`
  - Passed
- Full backend: `uv run pytest backend`
  - `202 passed, 7 warnings`
- Diff hygiene: `git diff --check`
  - Passed
- Local render smoke: `curl -sS -D - http://localhost:3000/`
  - Returned `HTTP/1.1 200 OK` and rendered the QuizCraft shell.
  - Browser screenshot was not captured because the in-app browser and local
    Playwright package were unavailable in this session.

## Remaining acceptance items

- Wrong-answer flashcards for short-answer/fill-blank still need explicit
  public API behavior coverage beyond the current generic creation path.
- FSRS scheduling, due-card review sessions, Anki export, and full management
  flows remain out of scope for #20 or later dependent issues.

## Blockers

- None for the next local increment. Existing project-level real LLM and
  production migration blockers still apply.

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
