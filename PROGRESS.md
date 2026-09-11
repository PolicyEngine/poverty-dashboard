# PR #6 review-fix progress

## State
Worktree `/Users/maxghenis/spm-rebuild-20260908/worktrees/poverty-serving-audit-20260910`,
branch `max/poverty-serving-audit-20260910`, base `cb4b8550` (= remote head of
`max/canonical-spm-runtime-20260909`). Lane 1 died on a usage limit after
committing all four fixes locally; nothing pushed.

## Done (inherited from lane 1, pending verification)
- `082f542` finding 1 — state_fips silent-default guard
- `33c1c22` finding 2 — .gitignore / data-directory materialization
- `76a7b1d` finding 3 — recompute cost guidance
- `e5b8d26` finding 4 — legacy diagnostics resolve_dataset

## Next
1. Verify each fix against the installed libraries (API claims, not just green tests)
2. Verify each new test fails before its fix and passes after
3. Run full suite: ruff format --check, ruff check, pytest (expect 39+)
4. Push with --force-with-lease to cb4b8550, then `gh pr checks 6 --watch`
