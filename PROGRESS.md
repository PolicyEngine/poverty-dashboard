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
- `all_region_codes()` == 52; `/recompute` fans out via `compute_region_remote.starmap`
  one container per region (modal_app.py:172-174) and `compute_local --all` loops the 52
  codes serially in one process (compute_local.py:56-63) — both doc claims are true.
- END TO END on the real population with the new guards in place: `compute_region("us")`
  345,685,947 people @ 13.173%; `compute_region("state/ca")` 40,077,002 @ 18.379%;
  `compute_region("state/wy")` 597,907 @ 6.889%. The state mask discriminates (CA is not
  the national total) and neither guard blocks a real region.
- Every materializable filename under data/ is ignored and the three numeric assets are
  not (`git check-ignore -v` on 8 paths).
- Scope: cb4b855..e5b8d26 touches only .gitignore, DEPLOYMENT.md, README.md,
  poverty_dashboard/poverty_calc.py and the two test files. frontend/, .github/,
  pyproject.toml, uv.lock, modal_app.py and the three data/*.json assets are untouched.
- PR #6 at cb4b8550: Python and Frontend checks pass; MERGEABLE / CLEAN.

## Lane 2 additions (pushed)
- `e080dc8` corrected three inaccurate mechanism claims the fixes introduced (Modal
  scalar cpu/memory are reservations not ceilings; starmap sets no max_containers so
  downloads are an upper bound of 52; the pinned manifest has metadata_sha256 None so
  no `.metadata.json` sibling is written) and made the materialization test pin each
  of the three ignore rules individually.
- `970e4e4` recorded that a regenerated diagnostics asset would carry the local path,
  not the registry URI, as its `dataset_path`.
- Adversarial audit: 29 agents, 20 claimed defects, 18 refuted; the one survivor was
  the `.metadata.json` overclaim, fixed in `e080dc8`.

## Done — pushed and green
Pushed `cb4b855..970e4e4` to `max/canonical-spm-runtime-20260909` (fast-forward,
--force-with-lease held). CI run 34623561335 on headSha 970e4e4: Frontend pass,
Python pass, `gh pr checks` exit 0; PR MERGEABLE / CLEAN.
Suite on the pushed tree: ruff format --check 0, ruff check 0, pytest 47 passed 0.

This file is intentionally NOT part of the pushed branch; the push set was built by
cherry-picking only the six fix commits onto cb4b855.

Report: rollout/fable-continuation-20260911/out/pov-6-fixes-r2.md
