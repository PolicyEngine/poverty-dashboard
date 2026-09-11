# PR #6 review-fix progress

## State
Worktree `/Users/maxghenis/spm-rebuild-20260908/worktrees/poverty-serving-audit-20260910`,
branch `max/poverty-serving-audit-20260910`, base `cb4b8550` (= remote head of
`max/canonical-spm-runtime-20260909`, re-verified 2026-09-11). Lane 1 died on a
usage limit after committing all four fixes locally; nothing pushed. Lane 2 is
verifying, not re-implementing.

This file is lane bookkeeping and is deliberately EXCLUDED from the push to the PR
branch (the assignment forbids unrelated files in the PR).

## Done
- `082f542` finding 1 — state_fips silent-default guard
- `33c1c22` finding 2 — .gitignore / data-directory materialization
- `76a7b1d` finding 3 — recompute cost/memory/timeout guidance
- `e5b8d26` finding 4 — legacy diagnostics resolve_dataset

## Verified (lane 2, 2026-09-11)
- `uv run ruff format --check .` exit 0; `uv run ruff check .` exit 0;
  `uv run pytest` 44 passed exit 0 (39 pre-existing + 5 new).
- Each of the 5 new tests fails when only its fix's source change is reverted
  (finding 1: 2 tests, findings 2/3/4: 1 test each).
- Against the REAL certified population (`data/populace_us_2024.h5`, symlinked into
  the HF cache): `get_known_periods("state_fips")` returns 12 year periods
  (2024-2035) and `calculate("state_fips", 2026, map_to="person").nunique()` == 51
  over 166321 person rows. Both new guards pass on production data.
- Modal limits cpu 2.0 / 8192 MiB / 1200 s and gateway 2400 s are unchanged since the
  initial scaffold `955f509`, i.e. predate `8692b92` (2026-09-09) which made every
  region a national-size masked run — the new doc claim is accurate.
- `all_region_codes()` == 52.
- PR #6 at cb4b8550: Python and Frontend checks pass; MERGEABLE / CLEAN.

## Next
1. Adversarial verification workflow over the four fixes (running)
2. Address any surviving defect
3. Push fix commits only (exclude this file), then `gh pr checks 6 --watch`
