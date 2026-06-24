# Issue Tracker

QuizCraft tracks public work in GitHub Issues for `Aley3567/QuizCraft`.

Ralph and other implementation agents must not mutate GitHub issues, labels, PRs, or remote branches unless the current user request explicitly authorizes it. For unattended runs, issue discovery is read-only and local progress lives in `docs/progress/` plus `.codex-loop/`.

## Work Sources

- PRD issues are reference material, not implementation tickets.
- Slice issues are implementation candidates only after dependency gates pass.
- Phase 1 and Phase 2 may also have local slice plans in `docs/plans/SLICE_PHASE_*.md`; local slices can be used as fallback work when no GitHub issue is claimable.

## Ralph Queue

Before an unattended implementation run, the monitor should build a local queue snapshot:

- `.codex-loop/queue.json` for scripts and prompts
- `.codex-loop/queue.md` for human-readable review

The queue snapshot is derived from GitHub issues, labels, issue bodies, local progress files, and dependency rules.

## Drain Mode

For unattended Ralph runs, the monitor should keep invoking the Claude/Ralph runner while `.codex-loop/queue.json` has claimable work. It stops and notifies yufeng when no claimable work remains because the rest is blocked, human-owned, missing information, under review, already in progress, complete, wontfix, or otherwise gated.

Run only one Ralph implementation process per git worktree. Parallel work requires separate worktrees, separate locks/logs, and non-overlapping write scopes.
