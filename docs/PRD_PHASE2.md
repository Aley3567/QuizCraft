# QuizCraft Phase 2 PRD: Adaptive Learning & Study Planning

> Phase 2 of 4 | 2026-06-23 | Depends on Phase 1

---

## Problem Statement

Phase 1 gives the student a solid quiz-and-flashcard loop, but it's still a passive tool: the student decides what to study, when, and how much. This mirrors the real problem — students who cram 3-7 days before exams don't know *what they don't know*. They waste time re-reading material they already understand while neglecting gaps they can't see. They have multiple files per course (PPTs, textbook PDFs, notes) scattered without connection. And when they get a question wrong, they redo the same question instead of attacking the underlying concept from a new angle.

Phase 2 transforms QuizCraft from a quiz tool into an **adaptive learning engine** that diagnoses, teaches, plans, and tracks — closing the loop between "I uploaded my stuff" and "I'm ready for the exam."

---

## Solution

Phase 2 adds six capabilities on top of Phase 1:

1. **Adaptive Learning Engine**: A state machine per concept that diagnoses mastery with simple questions, teaches via document-grounded explanations when the student struggles, and only advances when understanding is demonstrated
2. **Exam Cram Mode**: Set an exam date, and the system auto-generates a day-by-day study plan (diagnose → consolidate → mock exam) that skips already-mastered content
3. **Study Kanban + Archive**: Visual board (To Learn | In Progress | Mastered) for tracking concept-level progress, with one-click archive to stop all recommendations for completed courses
4. **Course Folder Model**: Group multiple documents into a course, merge knowledge graphs, generate cross-document questions
5. **Error Variant Generation**: When a student gets a question wrong, generate new questions on the same concept from different angles — not the same question repeated
6. **Scene Tags (Exam vs Interview)**: Switch question type distribution and Bloom level emphasis based on study purpose

---

## User Stories

### Adaptive Learning Engine

1. As a student, I want the system to give me 2-3 simple diagnostic questions per concept when I start a new document, so that it can figure out what I already know vs. what I need to learn.
2. As a student, I want concepts I answer correctly in diagnosis to be marked as "mastered" and enter the FSRS review pool, so that I don't waste time on things I already know.
3. As a student, I want concepts I answer incorrectly to enter a teaching mode where the system explains the concept using my own document text, so that I learn from my course material, not generic explanations.
4. As a student, I want the teaching mode to present the relevant document passage first, then ask me to answer a follow-up question to verify I understood, so that the system confirms comprehension rather than assuming reading = understanding.
5. As a student, I want the adaptive flow to cycle (diagnose → teach → re-test → advance or re-teach) until I demonstrate understanding, so that no concept slips through with false mastery.
6. As a student, I want to see my concept-level mastery map (which concepts are mastered, in-progress, or untouched), so that I have a clear picture of my coverage.
7. As a student, I want to manually override a concept's status (e.g., mark as "already know" without answering), so that I can skip topics I'm confident about.
8. As a student, I want the adaptive engine to mix diagnosed/mastered/new concepts in review sessions (interleaving), so that I benefit from spaced interleaving even during the learning phase.
9. As a student, I want the system to detect when I'm stuck on a concept after multiple failed re-tests, and offer a different explanation approach or flag it for manual review, so that I'm not trapped in a loop.

### Exam Cram Mode

10. As a student, I want to set an exam date for a document or course (e.g., "exam in 3 days"), so that the system can plan my study schedule accordingly.
11. As a student, I want the system to auto-generate a day-by-day study plan based on the exam date and my current mastery state, so that I don't have to figure out what to study when.
12. As a student, I want Day 1 of the plan to focus on diagnosis + teaching (finding and filling gaps), so that I identify weak spots early.
13. As a student, I want middle days to focus on consolidation + spaced review of weak concepts, so that gaps are reinforced before the exam.
14. As a student, I want the last day to be a full mock exam with interleaved cross-topic questions matching expected exam format, so that I simulate the real test experience.
15. As a student, I want the cram plan to skip already-mastered concepts entirely, so that limited study time is spent only on what I need.
16. As a student, I want to see a progress bar showing how much of the plan I've completed vs. remaining, so that I know if I'm on track.
17. As a student, I want the plan to dynamically adjust if I'm ahead or behind schedule (e.g., if I master Day 1 topics faster, pull forward Day 2 content), so that the plan stays optimal in real-time.
18. As a student, I want to be able to extend or shorten the exam date after the plan is created, so that the system recalculates if my exam gets moved.
19. As a student, I want a "cram dashboard" that shows: days remaining, concepts mastered vs. total, estimated readiness score, and today's tasks, so that I have a single view of my exam prep status.

### Study Kanban + Archive

20. As a student, I want a kanban board view of my documents/courses with columns: To Learn | In Progress | Mastered, so that I can see my overall study status at a glance.
21. As a student, I want documents to automatically move between kanban columns based on concept mastery percentage (e.g., >80% mastered → "Mastered" column), so that the board reflects reality without manual updates.
22. As a student, I want to drag documents between columns manually to override automatic placement, so that I have control when the automatic logic doesn't fit my situation.
23. As a student, I want to archive a course or document with one click, which stops all flashcard reviews, quiz recommendations, and notifications for that material, so that finished courses don't clutter my active study.
24. As a student, I want to unarchive a course if I need to revisit it later, with all previous progress preserved, so that archiving is non-destructive.
25. As a student, I want the home dashboard to show: active courses count, cards due today, current streak, weekly study time, so that I have motivation and awareness at login.
26. As a student, I want to filter the kanban by course/subject tags, so that I can focus on one subject area at a time when I'm managing multiple courses.

### Course Folder Model

27. As a student, I want to create a "Course" and add multiple documents to it (e.g., 5 lecture PPTs + 1 textbook PDF + my notes), so that all material for one class is organized together.
28. As a student, I want the system to automatically detect overlapping concepts across documents in the same course and merge them, so that I don't get duplicate questions about the same topic from different files.
29. As a student, I want cross-document questions that combine knowledge from multiple sources (e.g., a concept from the PPT + an example from the textbook = one application question), so that my understanding is tested holistically.
30. As a student, I want every cross-document question to cite all source documents and pages it draws from, so that I can trace back to each original source.
31. As a student, I want to add or remove documents from a course at any time, with the knowledge graph and questions updating accordingly, so that I can incrementally build my course materials.
32. As a student, I want to see a unified concept map for the entire course (not per-document), so that I understand how topics across different lectures connect.

### Error Variant Generation

33. As a student, I want a "Practice variants" button on any wrong answer that generates 2-3 new questions on the same concept from different angles, so that I can attack my weak spot from multiple directions instead of redoing the same question.
34. As a student, I want variant questions to test the concept differently (e.g., if I failed an MCQ, the variant might be a short-answer or an application scenario), so that I build deeper understanding rather than memorizing one question format.
35. As a student, I want variant questions to also be source-anchored to my document, so that feedback on variants still cites my course material.
36. As a student, I want the system to automatically generate variants for concepts I've failed multiple times and add them to my next review session, so that persistent weak spots get extra attention without me manually requesting it.
37. As a student, I want to see which original question a variant was derived from, so that I can track the chain of my learning on a difficult concept.

### Scene Tags (Exam vs Interview)

38. As a student, I want to tag a course as "Exam prep" or "Interview prep" when creating it, so that the system adjusts its question strategy.
39. As a student, I want Exam mode to emphasize written-test question types (MCQ, fill-blank, true/false, calculation) with Bloom levels skewed toward Remember/Understand/Apply, so that practice matches exam format.
40. As a student, I want Interview mode to emphasize open-ended questions ("explain in your own words", "compare X and Y", "design a solution for...") with Bloom levels skewed toward Analyze/Evaluate, so that I practice articulating knowledge.
41. As a student, I want to switch a course's scene tag at any time, with question distribution recalculating for future sessions, so that I can repurpose materials (e.g., course exam done, now prepping for job interview on same topic).
42. As a student, I want the mock exam in cram mode to match the scene tag's question distribution, so that the simulated test feels like the real one.

---

## Implementation Decisions

### Adaptive Learning State Machine

Each Concept has a `mastery_state` with defined transitions:

```
               ┌─────────────┐
               │   Unknown    │  (initial state)
               └──────┬──────┘
                      │ start adaptive session
                      ▼
               ┌─────────────┐
          ┌────│  Diagnosing  │────┐
          │    └─────────────┘    │
     pass │                       │ fail
          ▼                       ▼
   ┌─────────────┐        ┌─────────────┐
   │   Mastered   │        │  Teaching   │
   └──────┬──────┘        └──────┬──────┘
          │                      │ read + follow-up
          │                      ▼
          │               ┌─────────────┐
          │          ┌────│  Re-testing  │────┐
          │          │    └─────────────┘    │
          │     pass │                       │ fail (count < 3)
          │          ▼                       ▼
          │   ┌─────────────┐         back to Teaching
          │   │   Mastered   │         (different explanation)
          │   └──────┬──────┘
          │          │               fail (count >= 3)
          │          │                      ▼
          │          │               ┌─────────────┐
          │          │               │    Stuck     │
          │          │               └─────────────┘
          ▼          ▼                (manual review)
   ┌──────────────────────┐
   │   FSRS Review Pool   │
   └──────────────────────┘
```

- State transitions are deterministic (no LLM in the decision). LLM is only used for generating teaching content and new test questions.
- "Pass" threshold for diagnosis: answer all diagnostic questions correctly. For re-testing: answer the follow-up question correctly.
- "Stuck" state triggers after 3 failed re-test cycles on the same concept. System flags it and suggests a different approach (e.g., "Try reviewing this section manually" or "Skip for now and revisit later").
- `mastery_state` stored on the Concept record. Transitions logged for analytics.

### Exam Cram Planner

Planning algorithm:

1. **Input**: Course/document, exam date, current concept mastery states
2. **Calculate available days** (exam_date - today)
3. **Categorize concepts**: Unknown (need full diagnosis+teach), Weak (diagnosed but not mastered), Mastered (in FSRS pool)
4. **Allocate phases**:
   - 1 day plan: diagnose all → teach failures → mock exam (compressed)
   - 2-3 day plan: Day 1 diagnose+teach, Day 2 consolidate, Last day mock exam
   - 4-7 day plan: Day 1-2 diagnose+teach, Day 3-5 consolidate+spaced review, Day 6-7 mock exam
   - 7+ day plan: spread diagnosis across 2-3 days, more consolidation days, 2 mock exams
5. **Daily task generation**: each day's plan is a concrete list of concepts to work on + session type (diagnostic/teaching/review/mock)
6. **Dynamic adjustment**: after each completed session, recalculate remaining plan based on actual results

Plan stored as `StudyPlan` → `DailyPlan[]` → `PlanTask[]` in database. Each task links to concepts and has a type enum (diagnose/teach/review/mock_exam).

The planner itself is **pure logic** (no LLM) — it only decides *what* to study *when*. Content generation (questions, teaching materials) delegates to existing Phase 1 engines.

### Course Manager — Concept Merging

When multiple documents are added to a course:

1. Extract concepts from each document independently (Phase 1 engine)
2. Run LLM-based semantic similarity check across all course concepts
3. Merge duplicates: keep the richest source_spans from all documents, link to all source documents
4. Generate a unified course-level concept list with cross-references
5. Cross-document question generation: prompt includes source material from multiple documents for a single concept, allowing questions that synthesize across sources

Data model additions:
- `Course`: name, scene_tag (exam/interview), archive status
- `Course` has many `Documents` (join table with ordering)
- `CourseConcept`: merged concept at course level, links to multiple document-level `Concepts` via `ConceptMapping` table
- Questions can reference multiple `source_spans` from different documents

Re-merge triggered when documents are added/removed from a course.

### Variant Question Generator

Given a wrong answer event:

1. Retrieve the concept, original question, user's wrong answer, and correct answer
2. Prompt LLM: "The student answered [wrong answer] to [question] about [concept]. The correct answer references [source_span]. Generate 2-3 new questions testing the same concept from different angles. Requirements: different question type than original, different wording, must be source-anchored, address the likely misconception behind the wrong answer."
3. Generated variants go through the same self-critique pipeline as Phase 1 questions
4. Variants link to the original question via `variant_of` foreign key

Auto-generation trigger: when a concept reaches 3+ wrong answers across all questions, system auto-generates variants and inserts them into the next review session.

### Scene Tag Configuration

Scene tags modify two parameters in the quiz generation engine:

| Parameter | Exam Mode | Interview Mode |
|-----------|-----------|----------------|
| Question type distribution | MCQ 40%, Fill-blank 20%, T/F 15%, Short-answer 25% | Short-answer 40%, Open-ended 30%, MCQ 15%, Scenario 15% |
| Bloom level weights | Remember 25%, Understand 30%, Apply 30%, Analyze 15% | Understand 15%, Apply 25%, Analyze 30%, Evaluate 25%, Create 5% |

Scene tag stored on Course (or Document if no course). Default: Exam. Switching recalculates distribution for future question generation only — existing questions are not regenerated.

### Kanban State Derivation

Kanban column is **derived**, not stored:

- **To Learn**: 0% concepts mastered (all Unknown state)
- **In Progress**: 1-79% concepts mastered
- **Mastered**: 80%+ concepts mastered

Manual drag override sets a `kanban_override` field on the document/course. User can clear override to return to auto-calculation.

Archive is a separate boolean flag. Archived items:
- Hidden from kanban by default (toggle to show)
- All FSRS reviews paused (due dates frozen)
- All cram plans deactivated
- Unarchive restores previous state and recalculates FSRS dues from today

### Dashboard Home

Aggregated view:
- Active courses count + per-course progress bars
- Cards due today (from FSRS across all active courses)
- Active cram plans with countdown + progress
- Weekly study time (derived from session timestamps)
- Streak counter (consecutive days with at least one review session)

---

## Testing Decisions

### Testing Philosophy

Same as Phase 1: test external behavior through module boundaries, mock LLM calls, use deterministic fixtures. Phase 2 introduces stateful flows (adaptive engine, cram planner), so tests must verify state transitions across sequences of actions.

### Seam 1: Adaptive State Machine (Unit Tests)

- Given concept in Unknown state + correct diagnostic answers → verify transition to Mastered + FSRS pool entry
- Given concept in Unknown state + wrong diagnostic answer → verify transition to Teaching
- Given concept in Teaching state + follow-up question answered correctly → verify transition to Mastered
- Given concept in Teaching state + follow-up failed → verify re-teach with different explanation approach
- Given concept with 3 consecutive re-test failures → verify transition to Stuck state
- Given concept manually overridden to Mastered → verify FSRS entry without diagnostic
- Verify interleaving: review session mixes concepts from different mastery states

No LLM calls — state machine transitions are deterministic. Mock the question/teaching content generators.

### Seam 2: Study Planner (Unit Tests)

- Given 10 concepts (5 Unknown, 3 Weak, 2 Mastered) + exam in 3 days → verify Day 1 has diagnostic+teaching tasks for Unknown concepts, Day 2 has consolidation for Weak, Day 3 has mock exam
- Given all concepts Mastered + exam in 2 days → verify plan is only mock exams (no diagnosis needed)
- Given exam tomorrow (1 day) → verify compressed plan with all phases in one day
- Given exam in 7 days → verify multi-day spread with appropriate phase allocation
- Given plan in progress + concept mastered mid-plan → verify remaining plan recalculates without that concept
- Given exam date change → verify plan regeneration with correct remaining days

Pure logic tests, no LLM. Planner is deterministic given inputs.

### Seam 3: Course Manager (Integration Tests via API)

- Create course → add 2 documents → verify concept extraction runs for both → verify merged concept list has deduped entries
- Add a third document with overlapping concepts → verify merge updates without duplicating
- Remove a document → verify concepts unique to that document are removed, shared concepts retain other sources
- Generate quiz for course → verify questions can reference multiple source documents
- Verify cross-document question source_spans point to valid text in their respective documents

LLM mocked for concept extraction and similarity checking. Database assertions on merged concept records.

### Seam 4: Variant Generator (Integration Tests via API)

- Given a wrong answer on an MCQ → request variants → verify 2-3 new questions returned with different question types
- Verify variant questions have valid source_spans in the original document
- Verify variant questions link to original question via variant_of
- Given 3+ wrong answers on same concept → verify auto-generation triggers and variants appear in next session
- Verify variants go through self-critique pipeline (mock both generation and critique)

LLM mocked. Tests verify orchestration (trigger logic, linking, pipeline flow).

---

## Out of Scope

- **Terminal challenge system** — Phase 3
- **Multi-user auth / OAuth** — Phase 4
- **Anki export** — Phase 4
- **FSRS parameter optimization** (auto-tuning from user's review history) — future enhancement
- **Collaborative study** (sharing courses between users) — not planned
- **AI-generated teaching videos or voice explanations** — not planned
- **Mobile app** — not planned
- **Multi-language UI** — Chinese only

---

## Further Notes

### Phase 2 Depends on Phase 1

All Phase 2 features build on Phase 1 infrastructure:
- Adaptive engine uses Phase 1's question generation + scoring + FSRS systems
- Cram planner orchestrates Phase 1's quiz sessions
- Course manager extends Phase 1's document parsing + concept extraction
- Variant generator extends Phase 1's question generation engine
- Scene tags modify Phase 1's quiz generation parameters

No Phase 2 feature replaces Phase 1 functionality — they layer on top.

### Key Design Principles for Phase 2

1. **State machine is deterministic**: The adaptive engine's decisions (diagnose/teach/test/advance) are pure logic based on answer correctness. LLM is only called for content generation, never for routing decisions. This makes the engine testable and predictable.

2. **Planner is reactive**: The cram plan recalculates after every session, not just at creation time. Plans are living documents, not static schedules.

3. **Concept merging is conservative**: When in doubt, keep concepts separate rather than over-merging. A false merge loses source specificity; a false split just means a few extra questions.

4. **Variants address misconceptions**: Variant questions aren't just "same topic, different words." They specifically target the likely misconception revealed by the student's wrong answer.

5. **Archive is a pause, not a delete**: All data is preserved. The student can resume at any time with full history intact.
