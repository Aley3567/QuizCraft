STATUS: IN PROGRESS

# Issue #21 - FSRS due-card review session

## 2026-06-24 Ralph iteration 1

Completed the first backend public API behavior increment for due-card review:
a newly created concept flashcard now appears in `GET /api/flashcards/due`,
can be rated through `POST /api/flashcards/{id}/review`, records a `ReviewLog`,
and moves out of the due queue after a Good review.

## What changed

- Added FSRS scheduling fields to `Flashcard`: `stability`, `difficulty`,
  `due_date`, `last_review`, `reps`, and `lapses`.
- Added `FlashcardRating` and `ReviewLog` for public review events.
- Added `GET /api/flashcards/due` for new and currently due cards.
- Added `POST /api/flashcards/{id}/review`, accepting Again/Hard/Good/Easy
  case-insensitively and updating schedule state deterministically.
- Added a public API behavior test covering new-card due listing, Good rating,
  review log creation, due-date update, and removal from the due queue.

## Verification

- RED: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - Failed as expected during collection because `ReviewLog` did not exist yet.
- GREEN: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - `5 passed, 7 warnings`
- Related: `uv run pytest backend/tests/test_answer_api.py backend/tests/test_flashcards_api.py -q`
  - `26 passed, 7 warnings`
- Full backend: `uv run pytest backend`
  - `205 passed, 7 warnings`
- Diff hygiene: `git diff --check`
  - Passed

## Remaining acceptance items

- Review endpoint accepts all ratings, but only the Good path is covered by the
  first public behavior test; Again/Hard/Easy should get explicit coverage in a
  later #21 increment.
- Review UI still needs the show-front, reveal-back, rate-card flow.
- The current scheduler is deterministic and FSRS-style over the required FSRS
  state fields; swapping in a packaged FSRS implementation remains a later
  refinement if the project adds the dependency.

## Blockers

- No blocker for the next local #21 increment.
- Existing project-level SQLite migration caveat applies: old dev DB files made
  before this commit will not get new `flashcards` columns or `review_logs` via
  `create_all`; delete/recreate the dev DB until Alembic is introduced.
