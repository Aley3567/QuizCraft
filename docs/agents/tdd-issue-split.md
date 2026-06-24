# TDD Issue Split

This document is the canonical issue split for QuizCraft implementation work.
It replaces the previous function-bucket slice split for agent execution.

## Split Rule

Every implementation issue must represent one observable user behavior, not one
internal subsystem.

Each issue must include:

- User behavior: what the user does and what they can observe.
- Public interface: API route, page, CLI command, or exported file format.
- First red test: the first failing behavior test to write.
- Minimal green: the smallest implementation that can pass that test.
- Completion signal: the local verification proving the behavior works.

Avoid issues whose first step is "add model", "build service", "create UI",
or "wire backend". Those are implementation steps inside a behavior issue.

## Mainline Queue

| Issue | Behavior slice | Status | Dependency |
| --- | --- | --- | --- |
| #16 | Draft question review loop | Ready | Existing Phase 1A + backend draft APIs |
| #17 | Quiz generation controls in the UI | Ready | Existing generation parameter APIs |
| #18 | Mixed question answering loop | Ready | Existing fill-blank and short-answer backend |
| #19 | LLM settings UI and runtime smoke | Ready | Existing settings backend |
| #20 | Flashcards from concepts and wrong answers | Blocked | #18 |
| #21 | FSRS due-card review session | Blocked | #20 |
| #22 | Flashcard management and review settings | Blocked | #21 |
| #23 | Course model and multi-document intake | Blocked | #22 |
| #24 | Course-level concept map and cross-document questions | Blocked | #23 |
| #25 | Exam cram plan from mastery state | Blocked | #24 |
| #26 | Adaptive diagnose-teach-retest loop | Blocked | #24 |
| #27 | Study dashboard, Kanban, and archive | Blocked | #25 and #26 |
| #28 | Single-user Docker deployment and password gate | Blocked | #22 |
| #29 | Anki export from scheduled flashcards | Blocked | #21 and #23 |
| #30 | Full data ZIP export and import | Blocked | #23 |
| #31 | Multi-user auth and data isolation | Blocked | #30 |
| #35 | Anki import and alternative export formats | Blocked | #29 |
| #36 | Production health, backup, and upgrade runbook | Blocked | #28 and #30 |
| #37 | User profile, admin, and per-user settings | Blocked | #31 |
| #38 | Versioned OpenAPI and programmatic access tokens | Blocked | #31 |

## Terminal Track

Terminal challenges are a separate track. They should not block the document
learning mainline.

| Issue | Behavior slice | Status | Dependency |
| --- | --- | --- | --- |
| #32 | Terminal sandbox challenge loop | Blocked | Stable single-user app shell |
| #33 | Generated terminal challenge review loop | Blocked | #32 |
| #34 | Theory-practice integration and challenge catalog | Blocked | #26 and #33 |

## TDD Issue Body Template

```md
## User behavior

The user ...

## Public interface

- ...

## First red test

- ...

## Minimal green

- ...

## Acceptance criteria

- [ ] ...

## Out of scope

- ...

## Agent Triage

- Role: `ready-for-agent` | `blocked-by-dependency`
- Type: `type:slice`
- Reason: ...
- Dependencies:
  - ...
- Claimable now: yes | no
- Suggested first increment: ...
- Verification:
  - ...
```

## Superseded Issues

The old function-bucket issues #5-#15 are superseded by #16-#38. They remain
useful as historical PRD notes, but agents should not claim them.
