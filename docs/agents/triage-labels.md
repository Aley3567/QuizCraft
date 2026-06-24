# Triage Labels

QuizCraft follows a Matt Pocock-style triage state machine, with one type label and one state label per issue.

## Type Labels

| Label | Meaning |
| --- | --- |
| `type:prd` | PRD or umbrella planning issue; source material, not directly implemented by Ralph |
| `type:slice` | Vertical implementation slice |
| `type:bug` | Defect fix |
| `type:chore` | Maintenance task |

## State Labels

| Label | Meaning |
| --- | --- |
| `needs-triage` | Maintainer or triage agent must evaluate the issue |
| `needs-info` | The issue is underspecified or waiting for more information |
| `ready-for-agent` | Fully specified and AFK-ready; use with dependency gates, not blindly |
| `ready-for-human` | Requires human judgment, credentials, external authority, or subjective acceptance |
| `blocked-by-dependency` | Specified, but cannot start until listed dependencies are complete |
| `agent-in-progress` | An agent has locally claimed or is actively working the issue |
| `needs-review` | Implementation exists and needs review |
| `done` | Completed and verified |
| `wontfix` | Will not be actioned |

## Agent Rule

Ralph may execute only issues that are both:

- claimable now after local dependency evaluation
- free of constraining state labels such as `blocked-by-dependency`, `ready-for-human`, `needs-info`, `needs-review`, `agent-in-progress`, `done`, or `wontfix`

If an issue has `Claimable now: no`, a constraining state label, or unsatisfied local dependencies, Ralph must skip it and write the reason into the local queue snapshot.

## Drain Rule

The Ralph monitor should keep invoking the Claude/Ralph runner while the queue has claimable work. It stops only when the global progress is complete, a run fails, a no-progress guard fires, or every unfinished item is constrained by dependency, human ownership, missing info, review, in-progress, done/wontfix, or another explicit gate.

Parallel Ralph execution is allowed only across isolated git worktrees with separate locks, logs, and branches. Do not run two implementation agents against the same worktree.
