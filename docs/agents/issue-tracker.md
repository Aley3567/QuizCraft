# Issue Tracker

QuizCraft tracks public work in GitHub Issues for `Aley3567/QuizCraft`.

Ralph and other implementation agents must not mutate GitHub issues, labels, PRs, or remote branches unless the current user request explicitly authorizes it. For unattended runs, issue discovery is read-only and local progress lives in `docs/progress/` plus `.codex-loop/`.

## Work Sources

- PRD issues are reference material, not implementation tickets.
- TDD behavior-slice issues are the implementation tickets. They must be split
  by observable user behavior and public interface, not by backend/frontend
  subsystem.
- `docs/agents/tdd-issue-split.md` is the canonical queue and issue body
  contract for implementation agents.
- Legacy slice plans in `docs/plans/SLICE_PHASE_*.md` are reference material.
  They can explain product intent, but they do not override the TDD issue split.

## Ralph Queue

Before an unattended implementation run, the monitor should build a local queue snapshot:

- `.codex-loop/queue.json` for scripts and prompts
- `.codex-loop/queue.md` for human-readable review

The queue snapshot is derived from GitHub issues, labels, issue bodies, local progress files, and dependency rules.

## Drain Mode

For unattended Ralph runs, the monitor should keep invoking the Claude/Ralph runner while `.codex-loop/queue.json` has claimable work. It stops and notifies yufeng when no claimable work remains because the rest is blocked, human-owned, missing information, under review, already in progress, complete, wontfix, or otherwise gated.

Run only one Ralph implementation process per git worktree. Parallel work requires separate worktrees, separate locks/logs, and non-overlapping write scopes.
