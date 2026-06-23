# QuizCraft Phase 3 PRD: Terminal Challenge System

> Phase 3 of 4 | 2026-06-23 | Depends on Phase 1, Phase 2

---

## Problem Statement

Theory-only learning breaks down for Linux and systems skills. A student can read about `chmod`, `grep`, or `systemd` in a textbook and answer quiz questions correctly, yet freeze at a real terminal when asked to actually fix a file permission issue or debug a failed service. The gap between "I can answer questions about it" and "I can do it with my hands" is enormous — and Phase 1/2's quiz + flashcard loop cannot bridge it.

As the student puts it: "我理论题全对，但打开终端就懵了 — 不知道从哪开始，命令记不住参数，一个 typo 就卡半天。" The problem is that muscle memory and procedural fluency only develop through repeated hands-on practice in a real (or real-enough) environment, with immediate feedback on whether the task was actually completed correctly.

Existing terminal learning platforms (KillerCoda, iximiuz Labs, Instruqt) solve this well — but they are cloud-hosted, proprietary, and their content cannot be linked to the student's own course materials. Phase 3 brings the same hands-on experience into QuizCraft: Docker-sandboxed terminal challenges generated from the student's own Linux textbooks, verified by check.sh scripts, and integrated with Phase 1/2's concept mastery tracking so that theory and practice reinforce each other.

---

## Solution

Phase 3 adds a terminal-based hands-on challenge system to QuizCraft:

1. **Docker Sandbox**: Spin up unprivileged, network-isolated Docker containers that serve as disposable Linux environments for each challenge
2. **Browser Terminal**: xterm.js embedded in the QuizCraft UI, connected to the container via WebSocket relay, providing a full interactive terminal experience
3. **Challenge Content Model**: Structured challenges consisting of Markdown instructions + setup.sh (environment preparation) + check.sh (verification) + cleanup.sh (teardown), following the KillerCoda/Katacoda pattern
4. **Verification Engine**: Execute check.sh inside the container — exit code 0 means pass, non-zero returns a hint message to guide the student. LLM-based judgment as fallback for tasks that resist scriptable verification.
5. **Auto-Generation Pipeline**: Parse Linux textbook sections and use LLM to generate hands-on exercises + verification scripts, with a mandatory human review gate before challenges become active
6. **Theory-Practice Integration**: Link terminal challenges to document concepts from Phase 1/2, update mastery state when challenges are completed, and surface related challenges when a student struggles with theory questions

---

## User Stories

### Sandbox Lifecycle

1. As a student, I want a fresh Docker container to start automatically when I begin a terminal challenge, so that I have a clean environment without leftover state from previous attempts.
2. As a student, I want the container to be ready in under 3 seconds, so that I don't lose focus waiting for the environment to spin up.
3. As a student, I want to reset my container with one click during a challenge, so that I can start over if I've made a mess without abandoning the whole challenge.
4. As a student, I want the container to be automatically destroyed when I finish or leave a challenge, so that resources are freed and no stale environments accumulate.
5. As a student, I want the system to enforce a time limit per challenge (configurable, default 30 minutes), so that forgotten containers don't consume resources indefinitely.
6. As a student, I want to see a warning 5 minutes before the time limit expires, so that I can save my progress or request an extension.
7. As a student, I want the container to have no network access by default, so that I'm practicing real skills rather than just googling answers inside the sandbox.
8. As a student, I want resource limits (CPU, memory, process count) enforced on the container, so that a runaway fork bomb or memory leak doesn't crash my host machine.
9. As a student, I want the system to support multiple container images (e.g., Ubuntu, CentOS, Alpine) depending on the challenge requirements, so that I practice in the environment the challenge expects.
10. As a student, I want to see the container status (running, stopped, timed out) in the UI at all times, so that I know whether my environment is alive.

### Terminal UI

11. As a student, I want a split-pane view with challenge instructions on the left and the terminal on the right, so that I can read instructions and type commands simultaneously without switching tabs.
12. As a student, I want the terminal to support copy-paste (Ctrl+Shift+C / Ctrl+Shift+V or right-click), so that I can paste commands from the instructions when appropriate.
13. As a student, I want the terminal to handle window resize and respond correctly (SIGWINCH), so that `vim`, `htop`, and other TUI programs render properly at any window size.
14. As a student, I want the terminal to automatically reconnect if the WebSocket connection drops briefly, so that a network hiccup doesn't lose my session.
15. As a student, I want the terminal to preserve scrollback history within the session, so that I can scroll up to see previous command outputs.
16. As a student, I want to adjust terminal font size, so that I can read comfortably on any screen.
17. As a student, I want the terminal to support standard keyboard shortcuts (Ctrl+C, Ctrl+D, Ctrl+Z, tab completion), so that it behaves like a real terminal I'd use on my own machine.
18. As a student, I want to toggle the instruction panel to full-width or collapse it, so that I can maximize terminal space when I don't need to reference instructions.

### Challenge Content

19. As a student, I want each challenge to have clear Markdown instructions explaining the task, expected outcome, and any constraints, so that I know exactly what to accomplish.
20. As a student, I want challenges organized by difficulty level (beginner, intermediate, advanced), so that I can start easy and progress at my own pace.
21. As a student, I want challenges organized by topic (file management, permissions, text processing, networking, services, shell scripting, etc.), so that I can focus on specific skill areas.
22. As a student, I want multi-step challenges where I complete a sequence of related tasks in a single session, so that I practice realistic workflows rather than isolated commands.
23. As a student, I want each step in a multi-step challenge to have its own check button, so that I get incremental feedback rather than only at the very end.
24. As a student, I want hints available for each challenge (progressive — first hint is vague, subsequent hints are more specific), so that I can get unstuck without seeing the full answer immediately.
25. As a student, I want to see a "show solution" option after at least two failed attempts, so that I can learn from the correct approach when truly stuck.
26. As a student, I want challenges to include a "why this matters" section linking the task to real-world use cases, so that the exercise feels purposeful rather than arbitrary.
27. As a student, I want the setup.sh script to pre-configure the environment (create files, install packages, set up scenarios) before I start, so that the challenge begins in a realistic state rather than a blank slate.

### Verification

28. As a student, I want to click a "Check" button at any time during a challenge to verify whether I've completed the task, so that I get feedback without guessing whether I'm done.
29. As a student, I want a clear pass/fail result with a specific hint message when I fail (e.g., "The file /etc/nginx/nginx.conf does not contain a server block listening on port 8080"), so that I know what's wrong without being told the exact answer.
30. As a student, I want the check to execute within 5 seconds, so that the verification loop is fast and I stay in flow.
31. As a student, I want partial progress tracked for multi-step challenges (e.g., "3 of 5 steps completed"), so that I can see how far I've gotten.
32. As a student, I want the verification to be deterministic and reliable — if I did the right thing, it should pass consistently — so that I trust the feedback.
33. As a student, I want LLM-based verification as a fallback for tasks where scripted checking is impractical (e.g., "write a shell script that does X" where multiple valid approaches exist), so that creative solutions aren't falsely rejected.
34. As a student, I want to see my command history reviewed after a failed check (optionally), so that the system can point out where I went wrong.

### Auto-Generation from Documents

35. As a student, I want the system to automatically generate terminal challenges from my uploaded Linux textbook chapters, so that hands-on practice is directly tied to what I'm studying.
36. As a student, I want each auto-generated challenge to reference the source section and page from my document, so that I can review the theory if I get stuck on the practical task.
37. As a student, I want auto-generated challenges to include both setup.sh and check.sh scripts, so that the environment is properly prepared and verification works automatically.
38. As a student, I want to preview and approve auto-generated challenges before they enter my practice pool, so that I catch any LLM errors in the exercise or verification logic.
39. As a student, I want to edit the generated instructions, check.sh, or setup.sh before publishing a challenge, so that I can fix issues or adjust difficulty.
40. As a student, I want the system to generate challenges at multiple difficulty levels for the same concept (e.g., basic `grep` usage, then regex `grep`, then `grep` in a pipeline), so that I have a progression path.
41. As a student, I want to regenerate challenges for a specific document section if the initial generation was poor quality, so that I'm not stuck with bad exercises.

### Integration with Theory (Phase 1/2)

42. As a student, I want terminal challenges linked to the same Concepts used in Phase 1/2 quizzes and flashcards, so that my mastery tracking reflects both theoretical and practical understanding.
43. As a student, I want completing a terminal challenge to update the linked concept's mastery state in the adaptive engine, so that demonstrated hands-on skill counts toward overall mastery.
44. As a student, I want the system to suggest relevant terminal challenges when I get a theory question wrong about a practical topic (e.g., wrong answer about `chmod` → suggest the permissions challenge), so that I reinforce theory through practice.
45. As a student, I want the system to suggest relevant theory review when I fail a terminal challenge repeatedly, so that I can go back to understand the concept before retrying the hands-on task.
46. As a student, I want terminal challenge completion to appear on my study kanban and cram plan alongside quiz and flashcard progress, so that I have a unified view of all learning activities.
47. As a student, I want the exam cram mode planner to include terminal challenges for practical topics when appropriate, so that cram plans cover both theory and hands-on skills.

### Challenge Management

48. As a student, I want to browse all available challenges in a catalog with filtering by topic, difficulty, and completion status, so that I can find what I want to practice.
49. As a student, I want to see my attempt history for each challenge (timestamps, pass/fail, time spent), so that I can track my improvement.
50. As a student, I want to re-attempt completed challenges, so that I can practice for muscle memory even after passing.
51. As a student, I want to create custom challenges manually (write my own instructions + check.sh), so that I can add exercises not covered by auto-generation.
52. As a student, I want to import/export challenges as structured files (JSON or YAML + scripts), so that I can share challenges or back them up.
53. As a student, I want to favorite/bookmark challenges for quick access, so that I can return to useful exercises easily.
54. As a student, I want challenge statistics on the dashboard (total completed, pass rate, average time, current streak), so that I can see my hands-on practice progress at a glance.

---

## Implementation Decisions

### Docker Sandbox Architecture

**Container Lifecycle**:
- Each challenge session creates a new Docker container from a specified base image
- Default image: `quizcraft/sandbox:ubuntu` (Ubuntu-based with common tools pre-installed)
- Additional images for specific challenge types: CentOS, Alpine, networking-focused (with iproute2, iptables), etc.
- Container runs unprivileged (`--security-opt=no-new-privileges`, no `--privileged`)
- Network isolation: `--network none` by default; challenges that require networking (e.g., setting up a web server) use an isolated bridge network with no external access
- Resource limits: `--memory=256m`, `--cpus=0.5`, `--pids-limit=100` (configurable per challenge)
- TTL enforcement: backend timer destroys containers that exceed the challenge time limit (default 30 min). A grace period warning is sent via WebSocket 5 minutes before expiration.
- Container states: `creating` → `running` → `stopped` (user-initiated or TTL) → `destroyed`
- Cleanup daemon: periodic sweep (every 60s) kills orphaned containers older than TTL

**Image Management**:
- Base images built via Dockerfile in the repository, versioned alongside the codebase
- `setup.sh` runs inside the container after creation to configure the challenge-specific environment (create files, users, install packages)
- Images are pulled/built at deployment time via Docker Compose; no runtime image pulls during challenge start

### WebSocket Terminal Relay

**Architecture**: `xterm.js (browser) ↔ WebSocket ↔ FastAPI endpoint ↔ docker exec` (or node-pty bridge)

Two implementation paths evaluated:

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **ttyd** | Standalone C binary that bridges PTY to WebSocket | Battle-tested, low resource, simple | Separate process per session, less control |
| **node-pty + ws** | Node.js PTY spawn + WebSocket server | Fine-grained control, programmatic | Adds Node.js dependency |
| **docker exec + FastAPI** | Python `docker exec -it` with asyncio stream relay | No extra dependencies, Python-native | More complex PTY handling in Python |

**Decision**: Use Python-native approach — FastAPI WebSocket endpoint that uses the Docker SDK (`docker-py`) to `exec_create` + `exec_start` with TTY, then relays stdin/stdout over the WebSocket. This keeps the stack Python-only (no Node.js dependency) and gives full programmatic control over the session lifecycle.

**Reconnection**: If the WebSocket drops, the container keeps running. On reconnect within TTL, the backend reattaches to the same exec session. If the exec session is gone (container restarted), a new exec is created in the same container.

**Data flow**:
```
Browser (xterm.js)
    │ WebSocket (binary frames)
    ▼
FastAPI WebSocket endpoint
    │ docker-py exec_start stream
    ▼
Docker container PTY (/bin/bash)
```

### Challenge Content Model

Each challenge is a bundle of:

```
challenge/
├── meta.yaml          # id, title, description, difficulty, topic, linked_concepts, 
│                      # base_image, time_limit, network_mode
├── instructions.md    # Student-facing Markdown with task description, steps, hints
├── setup.sh          # Runs inside container before student begins (creates files, 
│                      # installs packages, configures scenario)
├── check.sh          # Verification script — exit 0 = pass, exit 1 = fail + 
│                      # stdout as hint message
├── solve.sh          # Reference solution (shown after 2 failed attempts)
└── cleanup.sh        # Runs after challenge ends (optional, for logging/metrics)
```

**Multi-step challenges**: `check.sh` accepts a step number argument (`check.sh 1`, `check.sh 2`, etc.) and verifies only that step. `meta.yaml` declares the total step count and per-step descriptions.

**Hint system**: `check.sh` stdout on failure is parsed as the hint message. For progressive hints, instructions.md includes collapsible hint blocks at increasing specificity. The "show solution" button reveals `solve.sh` content.

**Storage**: Challenge bundles stored on the filesystem under `data/challenges/{challenge_id}/`. Metadata indexed in SQLite for querying/filtering.

### Verification Engine

**Primary: check.sh execution**
1. Student clicks "Check" → backend sends `docker exec` to run `check.sh` (or `check.sh {step}`) inside the container
2. Script has 10-second timeout (configurable). If it exceeds timeout → treated as failure with "Verification timed out" message.
3. Exit code 0 → pass. Non-zero → fail, stdout captured as hint message.
4. Result (pass/fail, hint, timestamp) stored in `ChallengeAttempt` record.

**Fallback: LLM verification**
For challenges flagged as `verification_mode: llm` in meta.yaml (e.g., "write a bash script that sorts a CSV by the third column" — where many valid approaches exist):
1. Collect: command history (from `~/.bash_history`), relevant file contents, environment state
2. Send to LLM with rubric: "The student was asked to [task]. Here is the container state. Did they accomplish the goal? Respond with pass/fail and explanation."
3. LLM verification is explicitly opt-in per challenge and never the default. check.sh is always preferred.

**Exit code convention**:
- `0`: All checks passed
- `1`: Check failed — stdout contains human-readable hint
- `2`: Environment error (check.sh itself has a bug) — reported differently in UI
- `124`: Timeout (if using `timeout` command wrapper)

### Auto-Generation Pipeline

**Input**: A document section from Phase 1 parsing that covers a Linux/systems concept (detected by topic classification).

**Pipeline**:
```
Document Section (parsed text + concept)
    │
    ▼
LLM Prompt: "Generate a hands-on terminal challenge for this concept"
    │
    ▼
Structured Output:
  - meta.yaml fields (title, description, difficulty, topic)
  - instructions.md content
  - setup.sh script
  - check.sh script  
  - solve.sh script
    │
    ▼
Quality Gate (automated):
  - Does check.sh use proper exit codes?
  - Does setup.sh avoid dangerous operations (rm -rf /, etc.)?
  - Is the instructions.md coherent and complete?
  - Does the difficulty match the source concept complexity?
    │
    ▼
Human Review Queue:
  - Student previews generated challenge
  - Can edit any file before publishing
  - Can reject and regenerate
  - Can test by running the challenge in a sandbox
    │
    ▼
Published Challenge (linked to source Concept + Document Section)
```

**LLM prompt strategy**:
- Include the source document text as context
- Provide 2-3 few-shot examples of well-structured challenges
- Request structured JSON/YAML output for meta fields + script content
- Instruct check.sh to test the final state, not the exact commands used (so multiple approaches are valid)
- Request setup.sh to create a realistic scenario rather than a blank environment
- Generate at 2-3 difficulty levels per concept when the concept supports it

**Difficulty calibration**:
- Beginner: single command, clear instructions, minimal context
- Intermediate: 2-5 commands, requires reading man pages or combining tools
- Advanced: multi-step workflow, debugging a broken state, scripting

### Integration with Phase 1/2

**Concept Linking**:
- `TerminalChallenge` has a `concept_id` foreign key to `Concept` (same entity used by Questions and Flashcards)
- When auto-generated from a document section, also stores `section_id` and `source_span` for traceability
- A single concept can have both theory questions (Phase 1) and terminal challenges (Phase 3)

**Mastery State Updates**:
- Completing a terminal challenge (all steps passed) triggers a mastery signal equivalent to answering a diagnostic question correctly in Phase 2's adaptive engine
- The adaptive engine's state machine treats challenge completion as evidence of practical mastery — a concept that was "Mastered" from theory alone can be further reinforced, and a concept in "Teaching" state can advance to "Mastered" via challenge completion
- FSRS impact: successful challenge completion is treated as a "Good" review for linked flashcards, updating their schedule

**Cross-recommendations**:
- When a student fails a theory question about a practical concept → UI shows "Try the hands-on challenge" link
- When a student fails a terminal challenge repeatedly → UI shows "Review the theory first" link with relevant document section
- Cram mode planner can schedule terminal challenges for practical topics alongside theory review sessions

### Data Model Additions

New entities for Phase 3:

- `TerminalChallenge`: challenge metadata — `id`, `title`, `description`, `difficulty` (beginner/intermediate/advanced), `topic`, `base_image`, `time_limit_seconds`, `network_mode` (none/isolated), `verification_mode` (script/llm), `step_count`, `concept_id` (FK to Concept), `section_id` (FK to Section), `source_span`, `status` (draft/review/published), `bundle_path` (filesystem path to challenge files), `created_at`, `updated_at`

- `ChallengeAttempt`: a single attempt at a challenge — `id`, `challenge_id` (FK), `started_at`, `ended_at`, `status` (in_progress/passed/failed/timed_out/abandoned), `steps_completed`, `total_checks` (number of times check was run), `container_id` (Docker container ID for reference)

- `ChallengeCheck`: individual check execution within an attempt — `id`, `attempt_id` (FK), `step_number`, `passed` (boolean), `hint_message` (from check.sh stdout), `executed_at`

- `ContainerSession`: tracks container lifecycle — `id`, `attempt_id` (FK), `container_docker_id`, `image`, `status` (creating/running/stopped/destroyed), `created_at`, `destroyed_at`, `destroy_reason` (completed/timeout/reset/cleanup)

Relationships:
```
TerminalChallenge ──→ Concept (FK, optional)
TerminalChallenge ──→ Section (FK, optional)
ChallengeAttempt ──→ TerminalChallenge (FK)
ChallengeAttempt ──→ ContainerSession (1:1)
ChallengeCheck ──→ ChallengeAttempt (FK)
```

---

## Testing Decisions

### Testing Philosophy

Same as Phase 1/2: test external behavior through module boundaries, use deterministic fixtures, mock external dependencies. Phase 3 introduces Docker as a new external dependency — tests must work without requiring a running Docker daemon (except for dedicated integration tests).

### Seam 1: Sandbox Lifecycle Manager (Unit Tests)

Test the container management layer in isolation by mocking the Docker SDK (`docker-py`):

- Given a challenge start request → verify `container_create` is called with correct image, resource limits (`--memory`, `--cpus`, `--pids-limit`), network mode (`--network none`), and security options
- Given a running container + reset request → verify old container is destroyed and a new one is created with the same configuration
- Given a running container that exceeds TTL → verify the manager destroys it and updates `ContainerSession.destroy_reason` to "timeout"
- Given a container in "creating" state + start failure → verify error state is recorded and user gets a clear error message
- Given the cleanup sweep runs → verify only containers older than TTL are destroyed; recent containers are untouched
- Verify container state transitions: `creating → running → stopped → destroyed` with no illegal transitions (e.g., `destroyed → running`)
- Given a WebSocket disconnect + reconnect within TTL → verify the same container is reused (no new container created)
- Given resource limit configuration per challenge → verify the correct limits are passed to Docker (not just the defaults)

Docker SDK calls mocked. Tests verify orchestration logic, state tracking, and correct parameter passing — not Docker behavior itself.

### Seam 2: check.sh Verification Engine (Unit Tests)

Test the verification execution and result parsing:

- Given check.sh that exits 0 → verify engine returns pass with no hint message
- Given check.sh that exits 1 + stdout "File not found at /etc/config" → verify engine returns fail with that exact hint message
- Given check.sh that exits 2 → verify engine reports environment error (distinct from task failure)
- Given check.sh that runs longer than the timeout (10s default) → verify engine kills the process and returns timeout failure
- Given a multi-step challenge + check for step 2 → verify engine calls `check.sh 2` (with step argument)
- Given a multi-step challenge with 3 steps, where steps 1 and 2 pass but step 3 fails → verify partial progress is recorded correctly (2/3 steps completed)
- Given check.sh that produces binary/garbage output on stdout → verify engine handles it gracefully (truncate or sanitize)
- Given LLM verification mode + mock LLM response "pass" → verify engine returns pass
- Given LLM verification mode + mock LLM response "fail" with explanation → verify engine returns fail with LLM explanation as hint

Docker exec calls mocked. LLM calls mocked. Tests focus on result parsing, timeout handling, and state recording logic.

### Seam 3: Exercise Generator (Integration/API Tests)

Test the auto-generation pipeline end-to-end (with mocked LLM):

- Given a document section about `chmod` (fixture) → call generation endpoint → verify response contains valid meta.yaml fields, non-empty instructions.md, setup.sh with proper shebang, check.sh with exit code pattern
- Given generated challenge output → verify automated quality gate catches: missing exit codes in check.sh, dangerous commands in setup.sh (`rm -rf /`), empty instructions
- Given a generated challenge that passes quality gate → verify it enters "review" status (not "published") — human review gate is enforced
- Given a challenge in "review" status + approval action → verify status transitions to "published" and concept_id linkage is recorded
- Given a challenge in "review" status + rejection → verify challenge is marked rejected and can be regenerated
- Given a document section with no practical component (e.g., pure theory about OS history) → verify generator either produces no challenge or produces a low-confidence result flagged for review
- Given generation at multiple difficulty levels → verify beginner/intermediate/advanced challenges test progressively deeper skills on the same concept

LLM mocked with pre-recorded responses. Tests verify pipeline orchestration: prompt construction, output parsing, quality gate enforcement, status management, concept linkage.

---

## Out of Scope

The following are explicitly **not** part of Phase 3:

- **Multi-user sandbox isolation** (separate Docker namespaces per user, quota management) — not needed for single-user self-hosted deployment
- **Kubernetes orchestration** (pod scheduling, auto-scaling sandbox pools) — overkill for personal use; Docker Compose is sufficient
- **Firecracker/gVisor/KubeVirt** — stronger isolation technologies reserved for multi-tenant scenarios that QuizCraft does not target
- **In-browser terminal without Docker** (WebAssembly-based Linux, e.g., WebVM) — interesting but too limited for real Linux practice; Docker gives a full environment
- **Network-enabled challenges by default** — all containers default to `--network none`; isolated networking is available per-challenge but no internet access
- **Real-time collaborative terminal** (shared terminal sessions, pair programming) — single-user product
- **IDE integration** (VS Code extension, embedded code editor) — terminal-only for Phase 3; code editing happens inside the terminal via vim/nano
- **Automated check.sh generation without human review** — LLM generates scripts but they MUST be reviewed before publishing; no fully autonomous content pipeline
- **Container image registry / marketplace** — custom images are built locally from Dockerfiles in the repository
- **Multi-user auth** — Phase 4
- **Anki export of terminal challenges** — Phase 4

---

## Further Notes

### Security Considerations for Docker Sandbox

Even for single-user self-hosted use, the sandbox must not compromise the host:

1. **No privileged containers**: All containers run unprivileged. `--security-opt=no-new-privileges` prevents privilege escalation.
2. **No host mounts**: Container filesystem is ephemeral. No volumes from the host are mounted into the sandbox (challenge files are copied in during setup.sh, not bind-mounted).
3. **Network isolation**: `--network none` by default. Challenges requiring networking use a dedicated Docker bridge network with no external routing.
4. **Resource limits are mandatory**: Every container has memory, CPU, and PID limits. A fork bomb inside the container hits the PID limit, not the host.
5. **TTL enforcement is non-negotiable**: No container survives beyond its TTL without explicit user interaction. The cleanup daemon is the safety net.
6. **check.sh runs as non-root inside the container**: The verification script should not require root privileges. If a challenge needs root for setup, setup.sh runs as root but check.sh runs as the challenge user.

### Content Quality and the Human Review Gate

Auto-generated challenges are the highest-leverage feature of Phase 3 — but also the highest-risk. A bad check.sh can pass when it shouldn't (false positive, student thinks they learned but didn't) or fail when it shouldn't (false negative, student gets frustrated by a correct solution being rejected). Both outcomes are worse than no challenge at all.

The human review gate is therefore non-negotiable:
- Every auto-generated challenge enters a "review" queue
- The student must preview the instructions, read the check.sh logic, and ideally test the challenge in a sandbox before publishing
- The "test in sandbox" flow: spin up a container, run setup.sh, follow the instructions, run check.sh, verify it passes — then publish
- This is extra work, but it's also pedagogically valuable: reviewing a verification script teaches the student what "correct" looks like

### Relationship Between Terminal Challenges and Existing Question Types

Terminal challenges are not a replacement for Phase 1/2 questions — they are a complement:

| Dimension | Quiz Questions (Phase 1) | Terminal Challenges (Phase 3) |
|-----------|-------------------------|-------------------------------|
| Tests | Declarative knowledge (what/why) | Procedural knowledge (how) |
| Format | Text answer | Command execution in real environment |
| Feedback | Source-cited explanation | check.sh pass/fail + hint |
| FSRS role | Primary review unit | Mastery reinforcement signal |
| Generation | From any document type | From Linux/systems content only |

A concept like "Linux file permissions" benefits from both: quiz questions testing "what does chmod 755 mean?" and a terminal challenge requiring the student to actually fix a permission issue on a running system.

### Docker Compose Integration

Phase 3 adds a new consideration to the deployment architecture. The QuizCraft application itself runs in Docker Compose, and now it needs to create Docker containers for sandboxes. This is Docker-outside-of-Docker (not Docker-in-Docker):

- The host's Docker socket (`/var/run/docker.sock`) is mounted into the QuizCraft backend container
- The backend uses `docker-py` to create sibling containers on the host
- Sandbox containers are on a separate Docker network from the application containers
- This approach is simpler and more performant than DinD, but requires the host to have Docker installed (already a requirement for Docker Compose deployment)

### Performance Budget

Target latencies for key operations:
- Container start (from cached image): < 2 seconds
- WebSocket terminal connection (after container is running): < 500ms
- check.sh execution: < 5 seconds for typical checks
- Challenge generation (LLM call): 10-30 seconds (acceptable since it's async and not in the practice loop)
- WebSocket reconnection: < 1 second
