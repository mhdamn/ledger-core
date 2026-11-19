# Worklog

Timestamps are the commit times recorded by git (container clock, ISO 8601).
The commit history is the authoritative timeline.

- 2026-11-19T08:16:44+00:00  chore: scaffold repository and worklog
- 2026-11-19T08:16:53+00:00  feat(money): currency precision, half-up rounding, exact equal split
- 2026-11-19T08:17:07+00:00  feat(core): ledger engine: postings, authorisation holds, settlement, reversal
- 2026-11-19T08:17:14+00:00  feat(core): end-of-day overdraft fees, daily interest, capitalisation
- 2026-11-19T08:17:53+00:00  feat(replay): scenario stream and per-day report

## Session notes

- The brief's E10 is listed after E9 but booked Day 5. Replayed by booked day (AMBIGUITIES #6).
- Hand-computed the full expected ledger before running the replay. The replay matched on every figure.
- Found four of the eight acceptance criteria to be wrong (REJECTED.md). Tests assert the corrected behaviour.
- Test-suite defects found on first run and fixed: a test that funded a ledger with 0.00 (the credit validator correctly rejects this), and a tautological "copy" assertion.
- Network access was not available in the build environment, so the repository was not pushed to GitHub from the build. It is delivered as a git bundle plus push instructions.
