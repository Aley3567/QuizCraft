# QuizCraft Phase 1 PRD: Core Learning Engine

> Phase 1 of 4 | 2026-06-23

---

## Problem Statement

University students who cram before exams (3-7 days out) face a broken study loop: they upload course materials to existing tools (Quizlet, Knowt, etc.) and get shallow, generic quiz questions that test surface-level recall. When they get a question wrong, the explanation doesn't reference *their* course content — it's a generic answer from the internet. Students end up on apps like "大学搜题酱" searching for explanations that still don't match what their professor taught, leading to confusion rather than understanding.

The core gap: no open-source tool combines document parsing, intelligent multi-type question generation, source-grounded error feedback, and spaced repetition into a single self-hosted system where users own their data and bring their own LLM.

---

## Solution

QuizCraft Phase 1 delivers a self-hosted web application that:

1. **Parses** uploaded PDF and Word documents through a tiered routing pipeline (fast local extraction → structured extraction → multimodal LLM fallback)
2. **Generates** quiz questions at multiple Bloom taxonomy levels, each anchored to a specific span in the source document
3. **Scores** answers (instant for objective types, LLM-evaluated for open-ended) and provides **error feedback that cites the user's own document** ("See page 37 of your courseware where it says...")
4. **Creates flashcards** from concepts and wrong answers, scheduled via the FSRS algorithm for optimal spaced repetition

The user uploads a document, gets intelligent questions, answers them, sees feedback grounded in their own materials, and reviews weak spots through FSRS-scheduled flashcards — all running on their own machine with their own LLM API key.

---

## User Stories

### Document Management

1. As a student, I want to upload a PDF file and have it automatically parsed into structured sections, so that I don't have to manually organize my study material.
2. As a student, I want to upload a Word (.docx) file with the same experience as PDF, so that I can use whatever format my professor provides.
3. As a student, I want to see a parsing progress indicator while my document is being processed, so that I know the system is working on large files.
4. As a student, I want the system to preserve tables, formulas, and images from my documents, so that STEM content isn't lost or garbled.
5. As a student, I want to see the parsed document structure (chapters, sections, key concepts extracted), so that I can verify the system understood my material correctly.
6. As a student, I want to delete a document and all its associated questions/flashcards, so that I can clean up materials I no longer need.
7. As a student, I want to re-parse a document if the initial parsing quality was poor, so that I can try a different parsing tier or updated content.

### Quiz Generation

8. As a student, I want to generate a quiz from my uploaded document with one click, so that I can immediately start practicing.
9. As a student, I want to control quiz parameters (number of questions, difficulty range, question types, chapter scope), so that I can tailor practice to my needs.
10. As a student, I want questions at multiple Bloom taxonomy levels (Remember, Understand, Apply, Analyze), so that I'm tested on both recall and deeper understanding.
11. As a student, I want a mix of question types (multiple choice, fill-in-the-blank, true/false, short answer), so that practice mirrors real exam formats.
12. As a student, I want every generated question to show which part of my document it came from (page number, section, highlighted span), so that I can verify the question is valid and find the relevant material.
13. As a student, I want multiple-choice distractors to be based on common misconceptions rather than obviously wrong answers, so that practice is genuinely challenging.
14. As a student, I want the system to avoid generating duplicate or near-duplicate questions for the same concept, so that my practice time isn't wasted.
15. As a student, I want to regenerate questions for a specific section if the current ones are too easy or irrelevant, so that I have control over question quality.
16. As a student, I want to preview and edit generated questions before they enter my practice pool, so that I maintain cognitive engagement and can fix any LLM errors.

### Quiz Taking & Scoring

17. As a student, I want to take a quiz in an interactive interface where I answer one question at a time, so that I can focus without being overwhelmed.
18. As a student, I want multiple-choice and true/false questions scored instantly after I answer, so that I get immediate feedback.
19. As a student, I want short-answer questions evaluated by the LLM with partial credit, so that I'm not unfairly penalized for wording differences.
20. As a student, I want to see detailed feedback after each question explaining why my answer was right or wrong, so that I learn from every attempt.
21. As a student, I want error feedback to **cite specific passages from my uploaded document** (e.g., "Your courseware page 37 states..."), so that explanations match what my professor taught rather than generic internet answers.
22. As a student, I want to see my quiz results summary (score, time spent, weak areas) after completing a session, so that I know where to focus next.
23. As a student, I want questions to be presented in **interleaved order** (mixing concepts and question types), not document order, so that I benefit from research-backed interleaving effects.
24. As a student, I want to flag a question as "bad question" if the LLM generated something incorrect, so that it's removed from my practice pool.

### Flashcard & FSRS Spaced Repetition

25. As a student, I want flashcards automatically generated from document concepts and my wrong answers, so that I don't have to manually create them.
26. As a student, I want to review flashcards in a session where I rate each card (Again / Hard / Good / Easy), so that the FSRS algorithm can optimize my review schedule.
27. As a student, I want the system to schedule my next review based on FSRS algorithm (not fixed intervals), so that I review at the optimal moment before I forget.
28. As a student, I want to set a target retention rate (e.g., 90%), so that I can balance review workload against memory strength.
29. As a student, I want to see how many cards are due today and a forecast of upcoming reviews, so that I can plan my study time.
30. As a student, I want to edit flashcard content (front/back text) after generation, so that I can fix errors or rephrase in my own words.
31. As a student, I want wrong quiz answers to automatically become higher-priority flashcards, so that my weakest areas get the most repetition.
32. As a student, I want a daily review limit setting, so that I'm not overwhelmed by too many cards in one session.

### Authentication & Access

33. As a self-hosting user, I want to protect my instance with a password, so that my study data isn't exposed on the network.
34. As a self-hosting user, I want to configure the password via environment variable, so that setup is simple and follows 12-factor conventions.
35. As a self-hosting user, I want my session to persist across browser refreshes (via cookie), so that I don't have to re-enter my password constantly.

### LLM Configuration

36. As a user, I want to configure which LLM provider and model to use (Claude, GPT, Gemini, or Ollama), so that I can use whatever API key I have or run locally.
37. As a user, I want to enter my API key through the web UI settings page, so that I don't have to edit config files.
38. As a user, I want the system to validate my LLM configuration with a test call before I start using it, so that I know the connection works.
39. As a user, I want to see estimated LLM cost per operation (parsing, question generation, scoring), so that I can make informed decisions about usage.

### Deployment

40. As a self-hosting user, I want to deploy with a single `docker compose up` command, so that setup is frictionless.
41. As a self-hosting user, I want all data stored in a single SQLite file, so that backup is as simple as copying one file.
42. As a self-hosting user, I want the application to work after initial setup without requiring any external services other than the LLM API, so that the dependency footprint is minimal.

---

## Implementation Decisions

### Architecture

- **Frontend**: React + Next.js (App Router), server-side rendering for initial load, client-side for interactive quiz/flashcard sessions
- **Backend**: Python FastAPI, async endpoints, serves as API layer between frontend and document processing / LLM calls
- **Database**: SQLite via an async-compatible ORM (SQLAlchemy async or Tortoise). Single file, zero config.
- **Deployment**: Docker Compose with two services (frontend, backend) + shared SQLite volume

### Data Model

Core entities and relationships:

- `Document`: uploaded file metadata, parsing status, raw file path
- `Section`: parsed structural unit of a document (chapter, heading block), with `content_text`, `page_start`, `page_end`, `section_path` (hierarchical breadcrumb like "Ch3 > 3.2 > Definition")
- `Concept`: extracted learning objective / key idea, linked to one or more Sections via `source_span` (exact text range in source)
- `Question`: generated quiz item — fields include `question_text`, `question_type` (mcq/fill_blank/true_false/short_answer), `correct_answer`, `distractors[]` (for MCQ, each with `text` + `explanation`), `bloom_level`, `difficulty`, `source_span` (reference back to document text), `concept_id`
- `QuizSession`: a quiz attempt — links to Questions, stores user answers, scores, timestamps
- `Answer`: user's response to a question — `user_answer`, `is_correct`, `score` (0-1 for partial credit), `feedback_text` (source-cited explanation)
- `Flashcard`: front/back text pair, linked to Concept and optionally to a wrong Answer. Contains FSRS scheduling fields: `stability`, `difficulty`, `due_date`, `last_review`, `reps`, `lapses`, `state` (new/learning/review/relearning)
- `ReviewLog`: each flashcard review event — `rating` (again/hard/good/easy), `timestamp`, `elapsed_days`, `scheduled_days`

### Document Parsing Pipeline

Tiered router architecture:

- **L1 (PyMuPDF4LLM)**: Default for all PDF pages. Fast, free, local. Extracts text + basic structure.
- **L2 (Docling)**: Escalation for pages where L1 output has quality issues (garbled tables, missing formulas, broken layout). Handles tables, formulas, multi-column.
- **L3 (Multimodal LLM)**: Last resort for scanned pages, handwriting, complex visual layouts. Sends page-as-image to the user's configured LLM with vision capability.
- **DOCX**: Pandoc (preferred, preserves structure/math) or Mammoth (DOCX-to-HTML-to-Markdown fallback).

Quality gate between tiers: heuristic checks on L1 output (text density per page, table detection, formula markers) determine whether to escalate. User can also manually trigger re-parse at a higher tier.

Chunking: structure-aware by section/heading, 512-1024 tokens per chunk, 10-20% overlap, preserving metadata (document_id, section_path, page_number, element type).

### Quiz Generation Engine

Two-step process:

1. **Concept Extraction**: LLM analyzes each section to extract 5-10 core learning objectives, misconceptions, key definitions. Output: structured list of Concepts with source_spans.
2. **Question Generation**: For each Concept, generate questions controlled by:
   - Bloom level distribution (configurable, default balanced across Remember/Understand/Apply/Analyze)
   - Question type mix (configurable)
   - Source-anchoring requirement: every question must include `source_span` referencing the document text that supports the question and answer
   - Self-critique pipeline: generate N questions, LLM self-rates on 6 dimensions (accuracy, clarity, difficulty, source-grounding, non-trivial, non-ambiguous), drop those scoring below threshold

Prompt engineering patterns (from research):
- Source-grounded generation with mandatory evidence spans
- Learning-objective-first extraction before question generation
- Bloom-controlled prompting with level justification
- Few-shot exemplars for higher-order question types
- Misconception-based MCQ distractors with per-distractor explanations

### Scoring & Feedback

- **Objective types** (MCQ, true/false, fill-blank): deterministic scoring, instant
- **Short answer**: LLM evaluation with rubric derived from the concept's source material. Returns score (0-1) + feedback
- **All feedback**: must include `source_citation` — the specific document passage that supports the correct answer. Format: "Your courseware [section/page] states: '[quoted text]'..."
- Wrong answers automatically enqueue the linked Concept into the flashcard pool with elevated priority

### FSRS Implementation

- Backend: `py-fsrs` library for scheduling calculations and parameter optimization
- Frontend: `ts-fsrs` for client-side next-review preview (no network round-trip needed for the "when is this card due" display)
- Default desired retention: 0.9 (90%)
- Card states: New → Learning → Review → Relearning
- Daily new card limit: configurable (default 20)
- Daily review limit: configurable (default 200)
- Review log stored for every rating event (enables future FSRS parameter optimization)

### Authentication

- Single-user model for Phase 1
- Password configured via `QUIZCRAFT_PASSWORD` environment variable
- Login endpoint returns httpOnly session cookie (signed JWT or session token)
- All API endpoints require valid session except the login endpoint
- No registration flow, no password reset — operator sets password in Docker env

### LLM Abstraction Layer

- Provider interface with implementations for: OpenAI-compatible (GPT, local Ollama), Anthropic (Claude), Google (Gemini)
- Configuration stored in SQLite settings table: provider, model, API key (encrypted at rest), base URL (for Ollama)
- Each operation type (parsing, concept extraction, question generation, answer scoring) can theoretically use different models, but Phase 1 uses a single configured model for all
- Structured output (JSON mode) used wherever possible for reliable parsing

### Offline Capability

- All generated content (questions, flashcards, FSRS state, feedback text) persisted to SQLite immediately after generation
- Frontend caches active quiz sessions and due flashcards locally
- Offline mode: objective question scoring works (deterministic), flashcard review works (FSRS is local math), but new question generation and short-answer scoring are unavailable
- When reconnected: pending short-answer scores are batch-evaluated

---

## Testing Decisions

### Testing Philosophy

Tests verify **external behavior through module boundaries**, not internal implementation. A good test for QuizCraft:
- Calls a public interface (API endpoint or module function)
- Asserts on the output shape and semantics
- Does NOT assert on internal state, private methods, or LLM prompt text
- Uses deterministic fixtures where possible; mocks LLM calls with recorded responses

### Seam 1: API Layer (Integration Tests)

Full request-response cycle through FastAPI test client:
- Upload document → verify parsing status transitions (pending → processing → complete)
- Generate quiz → verify response contains questions with required fields (source_span, bloom_level, question_type)
- Submit answers → verify scoring response with feedback containing source citations
- Flashcard review → verify FSRS scheduling returns valid next-due dates

LLM calls mocked at the provider abstraction layer with pre-recorded responses. SQLite uses in-memory database per test.

### Seam 2: Document Parser Router (Unit Tests)

- Given a known PDF fixture, verify L1 parser returns structured sections with text content
- Given a PDF with tables, verify L2 escalation triggers and returns table-aware output
- Given a DOCX fixture, verify Pandoc/Mammoth returns sections with preserved structure
- Verify chunking produces segments within token bounds with correct metadata
- Verify quality gate heuristics (text density, table markers) correctly route pages to appropriate tiers

No LLM calls — parser tests use local-only tiers (L1, L2). L3 tested separately with mocked vision responses.

### Seam 3: Quiz Generation Engine (Unit Tests)

- Given a fixed set of Concepts (fixture), verify generated questions have valid structure (all required fields present)
- Verify Bloom level distribution matches requested configuration
- Verify every question contains a non-empty source_span that exists in the source section text
- Verify MCQ distractors have explanations
- Verify self-critique pipeline filters low-quality questions (mock both generation and critique LLM calls)

LLM calls mocked. Tests focus on the orchestration logic (two-step process, filtering, config application), not LLM output quality.

### Seam 4: FSRS Scheduler (Unit Tests)

- Given a new card + rating "Good", verify next review is scheduled within expected range
- Given a card with 5 prior reviews + rating "Again", verify it enters relearning state
- Verify daily limits are respected (new card cap, review cap)
- Verify desired_retention parameter affects scheduling intervals
- Verify review log records are created for every rating event

No mocks needed — FSRS is deterministic math (`py-fsrs` library). Tests validate integration with the library and our scheduling logic around it.

---

## Out of Scope

The following are explicitly **not** part of Phase 1 and will be addressed in subsequent PRDs:

- **Adaptive learning engine** (diagnose → teach → test flow) — Phase 2
- **Exam cram mode** (auto-planned study schedule based on exam date) — Phase 2
- **Study kanban + archive mechanism** — Phase 2
- **Error variant question generation** (one-click generate new questions for wrong concepts) — Phase 2
- **Course folder model** (multi-document grouping, cross-document question generation, concept dedup) — Phase 2 (Phase 1 handles single documents independently)
- **Exam vs Interview scene tags** — Phase 2
- **Terminal challenge system** (xterm.js, Docker sandbox, check.sh verification) — Phase 3
- **Multi-user auth** (registration, OAuth, roles) — Phase 4
- **Anki .apkg export** — Phase 4
- **Mobile-responsive UI** — not scoped; desktop-first
- **Real-time collaboration** — not planned
- **Internationalization** — Chinese UI only for now

---

## Further Notes

### Key Research Findings That Inform Phase 1

1. **Interleaving is mandatory**: Questions must NOT be presented in document order. Mix concepts, question types, and difficulty levels within every quiz session. (Source: research/04_learning_science.md)

2. **Feedback without source grounding is harmful**: Users can memorize wrong answers if feedback is vague. Every answer feedback must cite the specific document passage. No citation = don't generate the question. (Source: research/04_learning_science.md, finding #2)

3. **User edit/preview step preserves learning benefit**: Pure auto-generation removes the cognitive engagement of creating study materials. The preview/edit step before questions enter the pool is not just QA — it's pedagogically valuable. (Source: research/04_learning_science.md, finding #8)

4. **FSRS is the industry direction**: SM-2 is being replaced across Anki, RemNote, Mochi, and Obsidian plugins. Starting with FSRS avoids a future migration. (Source: research/02_flashcard_spaced_repetition.md)

5. **Tiered parsing saves 90%+ cost**: Most PDF pages are clean digital text that L1 handles fine. Only escalate complex pages. A 300-page textbook might send only 30 pages to expensive L2/L3 processing. (Source: research/05_document_parsing_tech.md)

### Anti-Patterns to Avoid (from Research)

- Do NOT dump 100+ flashcards from a single document upload — drip-feed through FSRS scheduling
- Do NOT mark a card as "mastered" just because the user recognized the answer — require active recall
- Do NOT generate questions only from headings/titles — extract actual content concepts first
- Do NOT use weak MCQ distractors (random wrong answers) — base them on common misconceptions
- Do NOT hide the source material behind the feedback — make document citation the primary feedback mechanism

### Dependency on User-Provided LLM

Phase 1 requires a working LLM API key for core features (concept extraction, question generation, short-answer scoring). The system should gracefully degrade when no LLM is configured:
- Document parsing (L1, L2) works without LLM
- Flashcard review (FSRS) works without LLM
- Quiz generation, concept extraction, and open-ended scoring do NOT work without LLM
- The onboarding flow should guide users to configure their LLM before attempting quiz generation
