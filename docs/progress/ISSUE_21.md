STATUS: COMPLETE

# Issue #21 - FSRS due-card review session

## 2026-06-25 Ralph iteration 3

Completed the final backend public API coverage increment for the review
endpoint: Again, Hard, and Easy ratings now have explicit behavior tests through
`POST /api/flashcards/{id}/review`, including response state, deterministic
scheduled interval, due-list visibility, and `ReviewLog` persistence.

## What changed

- Added a parameterized public API test for the remaining review ratings.
- Verified title-case `Again`/`Hard`/`Easy` inputs are accepted by the endpoint
  and persisted as lowercase review log values.
- Confirmed Again keeps a newly reviewed card due immediately while Hard and
  Easy move the card out of the due queue with deterministic next intervals.
- No product code change was required; the previous backend implementation
  already satisfied the remaining rating behavior, but lacked explicit
  acceptance coverage.

## Verification

- Coverage check: `uv run pytest backend/tests/test_flashcards_api.py -q`
  - New public behavior test passed against existing implementation:
    `8 passed, 7 warnings`
- Related backend: `uv run pytest backend/tests/test_answer_api.py backend/tests/test_flashcards_api.py -q`
  - `29 passed, 7 warnings`

## Remaining acceptance items

- None for issue #21. Due-card query, all four review ratings, review log
  creation, deterministic card state/due updates, and the frontend flip/rate
  flow are covered.
- Packaged `py-fsrs` integration remains a future refinement outside this
  issue's current local acceptance scope if the project chooses to add that
  dependency.

## Blockers

- No blocker for issue #21.
- Existing project-level SQLite migration caveat applies: old dev DB files made
  before the #21 backend commit will not get new `flashcards` columns or
  `review_logs` via `create_all`; delete/recreate the dev DB until Alembic is
  introduced.

## 2026-06-25 Ralph iteration 2

Completed the frontend public behavior increment for daily due-card review:
the main QuizCraft page now exposes a due-card session, lets the user reveal
the card back, rate it Again/Hard/Good/Easy, and shows the next review interval
returned by the backend.

## What changed

- Added frontend API wrappers for `GET /api/flashcards/due` and
  `POST /api/flashcards/{id}/review`.
- Extended `FlashcardOut` with FSRS scheduling fields and added
  `FlashcardReviewOut` for the review response.
- Added `FlashcardReview`, a one-card-at-a-time session with front/back reveal,
  source citation display, four rating buttons, loading/error states, and
  post-review next-due feedback.
- Mounted the review session on the main page outside the active quiz state, so
  a user can open due-card review without first completing another quiz.

## Verification

- RED: `cd frontend && npm test -- --run src/lib/api.test.ts`
  - Failed as expected: `listDueFlashcards is not a function`.
- GREEN: `cd frontend && npm test -- --run src/lib/api.test.ts`
  - `19 passed`
- Full frontend: `cd frontend && npm test -- --run`
  - `35 passed`
- Frontend typecheck: `cd frontend && npm run typecheck`
  - Passed
- Frontend build: `cd frontend && npm run build`
  - Passed
- Related backend: `uv run pytest backend/tests/test_answer_api.py backend/tests/test_flashcards_api.py -q`
  - `26 passed, 7 warnings`
- Full backend: `uv run pytest backend -q`
  - `205 passed, 7 warnings`
- Diff hygiene: `git diff --check`
  - Passed
- Render smoke:
  - Started backend with a temporary SQLite DB and seeded one due concept card.
  - Started `cd frontend && npm run dev`.
  - Used Playwright with the installed Google Chrome binary at desktop
    1280x900 and mobile 390x844.
  - Desktop rendered one due card, revealed the back, showed Again/Hard/Good/Easy,
    submitted Good, displayed the recorded next-due message, and had no
    horizontal overflow.
  - Mobile 390px rendered the review panel with no horizontal overflow.

## Remaining acceptance items

- Explicit backend public API coverage for Again/Hard/Easy rating outcomes is
  still pending; the endpoint implementation and UI expose all four ratings,
  but only Good has backend route coverage so far.
- Packaged `py-fsrs` integration remains a later refinement if the project
  decides to add the dependency; the current scheduler is deterministic and
  FSRS-style over the required card state fields.

## Blockers

- No blocker for the next local #21 increment.
- Existing project-level SQLite migration caveat applies: old dev DB files made
  before the #21 backend commit will not get new `flashcards` columns or
  `review_logs` via `create_all`; delete/recreate the dev DB until Alembic is
  introduced.

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
