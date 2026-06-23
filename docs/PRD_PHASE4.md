# QuizCraft Phase 4 PRD: Ecosystem & Polish

> Phase 4 of 4 | 2026-06-23 | Depends on Phase 1, Phase 2, Phase 3

---

## Problem Statement

After three phases, QuizCraft has a complete learning engine: document parsing, adaptive quiz generation, spaced repetition, exam cram planning, study kanban, and terminal challenges. But a capable engine is not enough for an open-source project to thrive. Three practical gaps remain:

1. **Single-user ceiling**: Phase 1's password-based auth works for one person on one machine. The moment a student wants to share their deployment with a study group, a TA wants to host it for a class, or anyone runs it on a shared server, the system breaks down. There is no concept of "my data vs. your data."

2. **Data lock-in contradiction**: QuizCraft promises zero vendor lock-in, but right now there is no standard way to get your data *out*. A student who has invested weeks building flashcard decks, review history, and course structures has no export path. Anki users — the largest existing flashcard community — cannot bring their decks in or take QuizCraft decks out. This makes the open-source promise feel hollow.

3. **Adoption friction**: Self-hosted software lives or dies on deployment documentation. Without production deployment guides, health check endpoints, backup/restore procedures, and environment variable references, every new user is reverse-engineering the setup. Contributions stall because there is no API documentation for third-party integrations.

Phase 4 addresses all three: multi-user auth for sharing, data portability for trust, and operational polish for adoption.

---

## Solution

Phase 4 delivers four capability areas:

1. **Multi-User Authentication System**: Full registration/login flow with JWT tokens, optional OAuth (GitHub, Google), user profiles, role-based access (user/admin), and complete data isolation — upgrading from Phase 1's single-password model while preserving existing data.

2. **Anki Export & Import**: Bidirectional interop with the world's largest flashcard ecosystem. Export QuizCraft decks as `.apkg` files (Anki's native format) with scheduling state mapped from FSRS. Import existing `.apkg` decks into QuizCraft. Plus CSV and Markdown export for universal portability.

3. **Deployment & Operations**: Production-ready Docker Compose configuration, HTTPS/reverse proxy guidance, environment variable reference, backup/restore procedures, health check endpoints, version migration tooling, and resource usage monitoring.

4. **Data Portability & Interoperability**: Full data export/import (courses, documents, questions, flashcards, review history) as structured JSON inside a ZIP archive. Published OpenAPI/Swagger documentation for every endpoint. API versioning for stable third-party integrations.

---

## User Stories

### Multi-User Authentication — Registration & Login

1. As a new user, I want to register with an email address and password, so that I have my own account on a shared QuizCraft instance.
2. As a returning user, I want to log in with my email and password and stay logged in across browser sessions, so that I don't re-authenticate every time I open the app.
3. As a user, I want to log out from my account, so that my session is terminated when I'm done or using a shared computer.
4. As a user, I want to reset my password via email if I forget it, so that I'm not permanently locked out of my account and study data.
5. As a user who prefers social login, I want to register/login with my GitHub account via OAuth, so that I don't need to create yet another password.
6. As a user who prefers social login, I want to register/login with my Google account via OAuth, so that I can use my university Google account for convenience.
7. As an instance operator, I want to configure whether registration is open (anyone can sign up) or invite-only, so that I can control who uses my deployment.
8. As an instance operator, I want to disable OAuth providers I don't need (e.g., only allow GitHub, not Google), so that I can simplify the login page for my specific audience.

### Multi-User Authentication — Session & Token Management

9. As a user, I want my session to use short-lived access tokens (JWT) with automatic refresh, so that security is maintained without constant re-login.
10. As a user, I want to see my active sessions and revoke any of them, so that I can secure my account if I suspect unauthorized access.
11. As a user, I want the system to invalidate all my sessions when I change my password, so that a compromised password doesn't leave old sessions active.

### Multi-User Authentication — User Profiles & Preferences

12. As a user, I want to set a display name that appears on my dashboard, so that the interface feels personalized.
13. As a user, I want to configure my preferred LLM provider and API key in my profile, so that each user on a shared instance can use their own model/key.
14. As a user, I want to set my default FSRS parameters (target retention, daily limits) in my profile, so that my learning preferences persist across courses.
15. As a user, I want to change my email address, so that I can update my contact information without losing my account.

### Multi-User Authentication — Data Isolation & Admin

16. As a user, I want to see only my own courses, documents, questions, flashcards, and review history, so that other users' data never appears in my interface.
17. As a user, I want confidence that no other user can access my uploaded documents or study data via the API, so that my academic materials are private.
18. As an admin, I want to see a list of all registered users with basic stats (registration date, last active, storage used), so that I can manage my instance.
19. As an admin, I want to disable or delete a user account, so that I can handle abuse or inactive accounts on my instance.
20. As an admin, I want to see aggregate usage statistics (total documents, total LLM API calls, storage consumed) across all users, so that I can monitor resource consumption.
21. As an admin, I want to set per-user storage quotas, so that one user doesn't consume all the server's disk space with uploaded documents.

### Multi-User Authentication — Migration from Single-User

22. As an existing Phase 1/2/3 user upgrading to Phase 4, I want all my existing data (documents, courses, questions, flashcards, FSRS review history, terminal challenges) automatically assigned to my account during the first migration, so that I lose nothing from my prior study sessions.
23. As an instance operator upgrading from single-user to multi-user, I want a one-time migration command that creates the first admin account and assigns all existing data to it, so that the upgrade is seamless.

### Anki Export

24. As a student, I want to export a course's flashcard deck as an `.apkg` file, so that I can review my QuizCraft cards in Anki on my phone during my commute.
25. As a student, I want the exported `.apkg` to preserve my FSRS scheduling state (mapped to Anki-compatible fields), so that Anki doesn't reset my review progress and re-show cards I've already mastered.
26. As a student, I want the exported `.apkg` to include images extracted from my documents (embedded in card content), so that visual content like diagrams and formulas appears correctly in Anki.
27. As a student, I want to choose which courses or individual decks to export (not forced to export everything), so that I have control over what goes to Anki.
28. As a student, I want the exported Anki deck to use a proper note type with fields (Front, Back, Source, Tags), so that the cards are well-structured in Anki and I can search/filter by source document.
29. As a student, I want each exported card to carry tags reflecting its course name, document source, and concept, so that my Anki library stays organized.

### Anki Import

30. As an existing Anki user, I want to import an `.apkg` file into QuizCraft, so that I can bring my existing flashcard collection into the adaptive learning system.
31. As a user importing from Anki, I want the import to map Anki's scheduling fields to FSRS parameters (best-effort), so that my review progress is approximately preserved rather than starting from scratch.
32. As a user importing from Anki, I want imported cards to appear as a new course or be added to an existing course, so that they integrate naturally into my QuizCraft study flow.
33. As a user importing from Anki, I want media files (images, audio) embedded in the `.apkg` to be extracted and displayed on the imported cards, so that content fidelity is maintained.

### Alternative Export Formats

34. As a student, I want to export my flashcards as a CSV file (front, back, tags, source), so that I can open them in Excel, Google Sheets, or import into other flashcard tools.
35. As a student, I want to export my flashcards as a Markdown file (one card per section), so that I have a plain-text backup I can read and search without any special software.
36. As a student, I want to export quiz questions and their correct answers as a Markdown or PDF study guide, so that I can print them or read them offline as a review sheet.

### Deployment & Operations — Production Configuration

37. As an instance operator, I want a production-ready Docker Compose file with HTTPS termination guidance (Caddy/nginx/Traefik examples), so that I can deploy QuizCraft securely without being a DevOps expert.
38. As an instance operator, I want a complete environment variable reference documenting every configurable option (database path, LLM defaults, auth secrets, CORS origins, rate limits), so that I can configure the system without reading source code.
39. As an instance operator, I want a backup and restore guide that covers the SQLite database file and uploaded document storage, so that I can protect against data loss with a simple cron job.
40. As an instance operator, I want clear documentation for upgrading between QuizCraft versions (database migrations, breaking changes, rollback steps), so that I can update safely.

### Deployment & Operations — Health & Monitoring

41. As an instance operator, I want a `/health` endpoint that reports system status (database reachable, disk space, LLM provider connectivity), so that I can set up uptime monitoring.
42. As an instance operator, I want the `/health` endpoint to return a structured JSON response with individual component statuses, so that monitoring tools can parse it programmatically.
43. As an instance operator, I want a resource usage dashboard showing LLM API call counts and estimated costs per user, so that I can track spending and identify heavy users.
44. As an instance operator, I want storage usage metrics (total uploaded documents size, database size) visible in the admin panel, so that I can plan capacity.

### Data Portability — Full Export/Import

45. As a user, I want to export all my data (courses, documents, questions, flashcards, review history, settings) as a single ZIP file containing structured JSON, so that I have a complete portable backup of everything I've built in QuizCraft.
46. As a user, I want the export ZIP to include my uploaded document files (PDFs, DOCX), so that the backup is fully self-contained and I can restore on a fresh instance.
47. As a user, I want to import a previously exported ZIP file into a new QuizCraft instance and have all my data restored (courses, documents, questions, flashcards, review history), so that I can migrate between servers or recover from data loss.
48. As a user, I want the import process to handle ID conflicts gracefully (e.g., if the target instance already has data), so that importing doesn't corrupt existing data.
49. As a user, I want to see a preview of what will be imported (number of courses, documents, flashcards) before confirming the import, so that I can verify I selected the correct export file.

### Data Portability — API Documentation & Interop

50. As a developer, I want OpenAPI/Swagger documentation auto-generated from the FastAPI backend and accessible at `/docs`, so that I can understand every available endpoint without reading source code.
51. As a developer, I want the API to use versioned URL prefixes (e.g., `/api/v1/...`), so that breaking changes in future versions don't silently break my integration.
52. As a developer, I want API authentication to support both session cookies (for the web UI) and Bearer tokens (for programmatic access), so that I can build scripts and integrations against the API.
53. As a developer, I want consistent error response formats across all endpoints (status code, error code, human-readable message), so that my integration handles failures predictably.

---

## Implementation Decisions

### Auth Architecture

**Token strategy**: JWT-based with two token types:
- **Access token**: short-lived (15 minutes), signed with HS256, contains `user_id`, `role`, `exp`. Sent as Bearer header for API calls; stored in memory (not localStorage) on the frontend.
- **Refresh token**: long-lived (7 days), opaque random string stored in the `refresh_tokens` database table. Sent as httpOnly secure cookie. Rotated on each use (old token invalidated, new one issued).

**Password handling**: bcrypt with cost factor 12. Passwords validated against minimum length (8 characters) on the backend. No maximum length (bcrypt truncates at 72 bytes — documented in UI).

**OAuth2 flow**: Authorization Code Grant via `authlib` library. Supported providers: GitHub, Google. Each provider can be independently enabled/disabled via environment variables (`OAUTH_GITHUB_CLIENT_ID`, `OAUTH_GITHUB_CLIENT_SECRET`, `OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET`). If neither is configured, OAuth buttons are hidden from the login page. OAuth accounts are linked by email — if a user registered with email first, then logs in via GitHub with the same email, the accounts merge.

**Registration modes**: Controlled by `QUIZCRAFT_REGISTRATION` env var:
- `open` (default): anyone can register
- `invite`: admin generates invite codes; registration requires a valid code
- `disabled`: no new registrations (admin creates accounts manually)

**Role model**: Two roles — `user` (default) and `admin`. First registered user on a fresh instance is automatically admin. Subsequent admins promoted via admin panel or CLI command.

### Database Migration for Multi-User

All existing tables gain a `user_id` foreign key column referencing the new `users` table. Affected tables:
- `documents`, `sections`, `concepts`, `questions`, `quiz_sessions`, `answers`, `flashcards`, `review_logs`, `courses`, `course_documents`, `course_concepts`, `study_plans`, `daily_plans`, `plan_tasks`, `terminal_challenges`

Migration strategy:
1. Create `users` table and `refresh_tokens` table
2. Run one-time migration: create a single admin user (prompted for email/password via CLI or env vars `QUIZCRAFT_ADMIN_EMAIL` / `QUIZCRAFT_ADMIN_PASSWORD`)
3. Add `user_id` column to all existing tables, defaulting to the newly created admin user's ID
4. Add NOT NULL constraint and foreign key after backfill
5. Add `user_id` to all composite indexes for query performance
6. Every API endpoint adds `WHERE user_id = current_user.id` to all queries (enforced at the ORM/repository layer, not ad-hoc in each endpoint)

**Data isolation enforcement**: A `UserScopedQuery` mixin or repository base class automatically applies `user_id` filtering. Admin endpoints bypass this for aggregate queries only (never for reading individual user data without explicit intent).

### Anki .apkg Format

The `.apkg` format is a ZIP file containing two SQLite databases:
- `collection.anki2` (or `collection.anki21`): contains notes, cards, decks, deck config, note types, and review logs
- `media`: a JSON file mapping numeric filenames to original filenames, plus the media files themselves

**Note type mapping**: QuizCraft flashcards export as a custom note type "QuizCraft" with fields:
- `Front`: card front text (HTML)
- `Back`: card back text (HTML)
- `Source`: document reference (e.g., "Linear Algebra - Chapter 3, p.42")
- `Tags`: space-separated tags (course name, concept name, scene tag)

**Card template**: Two templates — "Forward" (Front → Back) and "Reverse" (Back → Front, optional per card).

**Scheduling field mapping** (FSRS → Anki):

| QuizCraft (FSRS) | Anki Field | Mapping |
|-------------------|------------|---------|
| `state` (new/learning/review/relearning) | `type` (0=new, 1=learning, 2=review, 3=relearning) | Direct enum mapping |
| `due_date` | `due` | Convert to Anki epoch-days (days since collection creation for review cards, epoch-ms for learning cards) |
| `stability` | `data` JSON field | Store as `{"s": value}` in Anki's custom data (Anki FSRS reads this) |
| `difficulty` | `data` JSON field | Store as `{"d": value}` |
| `reps` | `reps` | Direct copy |
| `lapses` | `lapses` | Direct copy |
| `last_review` | `odue` or computed | Best-effort; Anki uses `ivl` (interval in days) which is derived |

Since Anki 23.10+ natively supports FSRS, the export targets FSRS-aware Anki format. Cards exported from QuizCraft should continue their scheduling in Anki without a cold restart.

**Import mapping** (Anki → QuizCraft): Reverse of the above. For Anki decks using legacy SM-2 scheduling, the importer runs a best-effort conversion: `stability ≈ ivl * 0.9`, `difficulty` derived from Anki's `factor` field (`difficulty ≈ 11 - factor/100`). Imported cards enter FSRS as review-state cards with approximate parameters.

**Media handling**: Images referenced in card HTML (`<img src="...">`) are extracted from the `.apkg` media store and saved to QuizCraft's document storage. HTML references are rewritten to point to QuizCraft's media serving endpoints.

**Library**: Use Python's `zipfile` + `sqlite3` to read/write `.apkg` files directly. No external Anki library dependency — the format is stable and well-documented.

### Data Export Format

Full export produces a ZIP with this structure:

```
quizcraft-export-{username}-{date}.zip
├── manifest.json          # version, export date, user info, content summary
├── courses/
│   ├── course-{uuid}.json # course metadata, scene tag, archive status
│   └── ...
├── documents/
│   ├── doc-{uuid}.json    # document metadata, sections, concepts
│   ├── doc-{uuid}.pdf     # original uploaded file
│   └── ...
├── questions/
│   ├── course-{uuid}-questions.json  # all questions for a course
│   └── ...
├── flashcards/
│   ├── course-{uuid}-flashcards.json # cards with full FSRS state
│   └── ...
├── review-history/
│   ├── review-logs.json   # complete FSRS review log
│   └── ...
├── quiz-sessions/
│   ├── sessions.json      # all quiz attempt records with answers
│   └── ...
└── settings.json          # user preferences (LLM config excluded for security)
```

`manifest.json` includes a `schema_version` field (starting at `1`) to handle future format changes. Import validates `schema_version` and refuses files from incompatible future versions.

Import conflict resolution: import generates new UUIDs for all records. If importing into an instance that already has data, imported courses appear as new courses (no merge attempt). User can manually merge or reorganize after import.

### API Versioning

All endpoints move under `/api/v1/` prefix. The unversioned paths (`/api/...`) redirect to the latest version during a transition period. When a breaking change is needed in the future, a `/api/v2/` is introduced while `/api/v1/` continues to work for at least 6 months (documented deprecation timeline).

FastAPI's `APIRouter` with prefix handles this cleanly. OpenAPI docs are generated per version.

### Health Check Endpoint

`GET /health` returns:

```json
{
  "status": "healthy",           // or "degraded" or "unhealthy"
  "version": "4.0.0",
  "checks": {
    "database": {"status": "up", "latency_ms": 2},
    "disk": {"status": "up", "free_gb": 45.2, "used_gb": 1.8},
    "llm": {"status": "up", "provider": "openai", "latency_ms": 340}
  },
  "timestamp": "2026-06-23T12:00:00Z"
}
```

The LLM check is optional (only runs if a default LLM is configured at the instance level). Individual user LLM configs are not checked here — that's a user-level concern, not an infrastructure concern.

---

## Testing Decisions

### Testing Philosophy

Same as prior phases: test external behavior through module boundaries, mock LLM calls, use deterministic fixtures. Phase 4 introduces security-sensitive flows (authentication, data isolation) where tests must verify *absence* of access, not just presence.

### Seam 1: Auth System (Integration Tests via API)

Full request-response cycle through FastAPI test client:

- Register with email + password → verify 201 response with user ID, verify password is not returned
- Register with duplicate email → verify 409 Conflict
- Register when mode is `invite` without code → verify 403 Forbidden
- Register when mode is `invite` with valid code → verify success and code is consumed
- Login with correct credentials → verify access token + refresh token cookie returned
- Login with wrong password → verify 401, verify no timing side-channel (constant-time comparison)
- Access protected endpoint without token → verify 401
- Access protected endpoint with expired access token → verify 401
- Refresh token → verify new access token issued + old refresh token invalidated
- Use revoked refresh token → verify 401 (token rotation detection)
- OAuth flow: mock GitHub/Google token exchange → verify user created or linked
- Password change → verify all existing sessions invalidated
- **Data isolation**: User A creates a course → User B queries courses → verify User A's course is NOT in User B's response
- **Data isolation**: User B tries to access User A's document by ID directly → verify 404 (not 403, to avoid ID enumeration)
- Admin lists users → verify response includes user stats
- Non-admin tries admin endpoint → verify 403

### Seam 2: Anki Exporter/Importer (Unit Tests)

- Given a set of 10 flashcards with FSRS state → export as `.apkg` → verify the ZIP contains valid SQLite databases
- Open the exported `collection.anki21` → verify note count matches, fields are populated, note type "QuizCraft" exists
- Verify FSRS → Anki scheduling field mapping: given a card with stability=30.0, difficulty=5.5, state=review → verify Anki card has correct `type`, `ivl`, `data` JSON
- Given flashcards with embedded images → export → verify media files present in ZIP and HTML references rewritten
- Given a card with CJK characters → export → verify encoding is correct in Anki database
- **Import path**: given a known `.apkg` fixture (created by Anki) → import → verify flashcards created with correct front/back text
- Import `.apkg` with SM-2 scheduling → verify FSRS parameters are approximated (stability, difficulty within expected ranges)
- Import `.apkg` with media → verify images extracted and card HTML updated
- Round-trip test: export from QuizCraft → import back → verify card count, text content, and FSRS state match original (within floating-point tolerance for scheduling fields)

### Seam 3: Data Export/Import (Integration Tests via API)

- User creates course with documents, questions, flashcards, review history → export → verify ZIP structure matches spec (manifest.json, correct subdirectories)
- Verify manifest.json contains correct schema_version and content counts
- Import the exported ZIP on a fresh instance → verify all records recreated with correct relationships (course → documents → concepts → questions → flashcards)
- Verify imported flashcard FSRS state matches original
- Verify imported original document files are present and accessible
- Import into instance with existing data → verify no collision (new UUIDs assigned, existing data untouched)
- Import ZIP with future schema_version → verify rejection with clear error message
- Import malformed ZIP (missing manifest, corrupt JSON) → verify graceful error, no partial state

---

## Out of Scope

The following are explicitly **not** part of Phase 4:

- **Mobile app**: QuizCraft remains a desktop-first web application. Anki export covers the mobile flashcard review use case.
- **Real-time collaboration**: No shared editing of courses, no live multiplayer quizzes. Each user works independently.
- **Commercial hosting / SaaS**: QuizCraft is self-hosted. No managed cloud offering, no payment processing, no subscription tiers.
- **Internationalization beyond Chinese**: The UI remains Chinese. English is not a priority for Phase 4 (English support is a future community contribution opportunity).
- **SSO / SAML / LDAP**: Enterprise identity providers are out of scope. OAuth (GitHub, Google) covers the common case. SAML/LDAP could be a community contribution.
- **Granular permissions / RBAC**: Only two roles (user, admin). No per-course permission sharing, no "viewer" vs. "editor" roles.
- **Automated backups**: Phase 4 documents backup procedures but does not implement scheduled automatic backups. Operators use cron + the documented procedure.
- **Plugin / extension system**: No third-party plugin architecture. The API is documented for external integrations, but there is no in-app plugin marketplace.
- **Anki sync protocol**: QuizCraft exports/imports `.apkg` files. It does not implement AnkiWeb's sync protocol for live bidirectional sync.
- **Data sharing between users**: No "share this course with a friend" feature. Each user's data is fully isolated. Sharing is done by exporting and sending the file.

---

## Further Notes

### Migration Path Is Critical

The upgrade from Phase 1-3 (single-user) to Phase 4 (multi-user) is the riskiest deployment operation in QuizCraft's lifecycle. Design principles for this migration:

1. **Zero data loss guarantee**: The migration must be idempotent and reversible. If it fails halfway, re-running completes it. A pre-migration backup prompt is mandatory.
2. **Offline migration**: The migration runs as a CLI command (`quizcraft migrate`), not as an automatic startup step. The operator controls when it happens.
3. **Backwards-compatible database**: After migration, the database schema works with Phase 4 code. Rolling back to Phase 3 code requires restoring the backup (documented).
4. **Single-user mode preserved**: If `QUIZCRAFT_REGISTRATION=disabled` and only one user exists, the UX should feel identical to Phase 1-3 — no unnecessary multi-user UI clutter.

### Open Source Considerations

Phase 4 is the phase that makes QuizCraft a proper open-source project rather than a personal tool:

- **API documentation** enables the community to build integrations (Obsidian plugins, CLI tools, browser extensions) without reading implementation code.
- **Data portability** gives users confidence to invest time in the platform — they know they can leave at any time with all their data.
- **Multi-user support** means a single deployment can serve a study group, a classroom, or a small community, expanding the user base beyond solo self-hosters.
- **Health checks and operational tooling** make it viable for others to run in production, not just "works on my machine."

### Anki Interop Strategy

The decision to support Anki's `.apkg` format is strategic:

- Anki has the largest flashcard user base globally. Many QuizCraft target users already have Anki decks.
- `.apkg` is a stable, documented format (SQLite inside ZIP) that hasn't had breaking changes in years.
- Anki 23.10+ supports FSRS natively, which means scheduling state can transfer cleanly in both directions.
- Supporting `.apkg` export gives QuizCraft users mobile flashcard review for free (via AnkiDroid / AnkiMobile) without QuizCraft needing a mobile app.

The import direction is equally important: a student with 2000 existing Anki cards shouldn't have to recreate them manually to benefit from QuizCraft's adaptive learning engine.

### Security Posture

Phase 4 introduces real security surface:

- **Password storage**: bcrypt only. No SHA-256, no MD5, no homebrew hashing.
- **JWT secrets**: Generated randomly at first boot, stored in environment variable (`QUIZCRAFT_JWT_SECRET`). If not provided, the application refuses to start (no silent fallback to a default key).
- **Refresh token rotation**: Every refresh token use invalidates the old token and issues a new one. If a stolen refresh token is used after the legitimate user has already rotated it, the entire token family is invalidated (detecting token theft).
- **Rate limiting**: Login endpoint rate-limited to 5 attempts per minute per IP. Registration rate-limited to 3 per hour per IP.
- **API key handling**: User LLM API keys are encrypted at rest (AES-256, key derived from `QUIZCRAFT_JWT_SECRET`). They are never returned in API responses after initial storage.
- **Upload validation**: Document uploads validated by file type, size limit (configurable, default 50MB), and MIME type. No arbitrary file storage.

### Dependency Summary

Phase 4 adds these new dependencies:

| Dependency | Purpose | License |
|------------|---------|---------|
| `python-jose` or `PyJWT` | JWT token creation/validation | MIT |
| `bcrypt` | Password hashing | Apache 2.0 |
| `authlib` | OAuth2 client for GitHub/Google | BSD |
| `python-multipart` | Form data parsing for file uploads (already likely present) | MIT |

No new frontend framework dependencies. The auth UI (login, register, profile pages) uses the existing React + Next.js stack.
