# Shipping a version

One entry point:

    python3 tv/ship.py vNNNN

`tv/ship_when_green.py` is the engine; `tv/ship.py` turns the system on and prints the
per-round report. Never `--no-verify` on main, never a force push to main, never a
token in the output. Main moves only through `hooks/pre-push`.

## The flow

1. **Box rehearsal** (`tv/preship.py`) — every gate that does not depend on the Mac:
   encoding-safe, swallow census, agreement laws (a law that pins a gate number must
   agree with that gate; attempt 7), blueprint, heart map, render_check (all targets,
   all five viewports), console-demos via `node tv/demo_console.mjs`, and the agent
   tests this push touches. Cheap deterministic checks run first. A red **blocks the
   ci/ push**.
2. **ci/ push** — `ci/claude-vNNNN` and `ci/proof-keys-vNNNN`. The hook skips the Mac
   on a ci-only push.
3. **Mac readiness** (a few seconds, attempt 8) — this worktree has `node_modules`
   (or a symlink to `~/d2r_bible_tests/node_modules`, which is the only safe auto-fix),
   `node -e "require('playwright')"` resolves, Playwright browsers (or system Chrome)
   are installed, the Python deps import, and no second-eye look is owed. Anything
   else fails loudly, before sitting on CI.
4. **CI wait, in parallel with the Mac hook rehearsal** — `preship.py --mac-rehearse`
   runs the hook's deterministic gates on this tree while GitHub grades the same
   commit. A rehearsal red is reported immediately, even if CI is still running.
5. **Make-up of failed jobs** — proof-keys shards still use REG-3270 (`gh run rerun
   --failed` when the only debt is cut proofs). Agent-tests and Playwright failed
   jobs are re-run the same way only when the flake ledger says they are a flake,
   or when the runner ended them. A genuine new red is left for a human. A healed
   flake drops out after 3 clean runs.
6. **Main**, through `hooks/pre-push` (the hook trusts GitHub's verdict and runs what
   GitHub cannot). The hook also re-checks Mac readiness as a backstop.
7. **Post-land** — watch Publish; ask the live console's `/api/status` whether it
   names this version (a silent console is said, not a refusal).

## Self-improvement

- `tv/preship_lessons.json` — every ship refusal that a cheap check could have caught,
  plus the check that now catches it. Adding a lesson is one entry; the law
  `test_every_preship_lesson_names_a_check_that_runs` refuses a check that does not
  exist or is not run. Seeded with bundle attempts 6, 7 and 8. A new preship refusal
  is appended automatically.
- `tv/shard_timings.json` — a row for every proof test, measured when a green
  proof-keys round has measured it, otherwise the median. The plan uses these rows
  to fill unpriced proofs. Updated after a green round. Law:
  `test_the_shard_balance_file_covers_every_proof_test`.
- `tv/flake_ledger.json` — known flakes, pruned after `nClean` (3) consecutive
  green runs.

## Time saved

Attempts 6, 7 and 8 each paid a full GitHub round (~60 minutes; the v3864 proof
shards alone ran 43–87 minutes, REG-3213 / ci_speed) before the Mac hook, or the
agreement law, refused. A local red now costs minutes. A flaky agent or Playwright
job re-runs only that job, not the green shards of the same workflow.

## Flags

    python3 tv/ship.py vNNNN
    python3 tv/ship.py vNNNN --no-box-rehearse --no-mac-ready --no-mac-rehearse
    python3 tv/preship.py                  # box rehearsal only
    python3 tv/preship.py --mac-ready
    python3 tv/preship.py --mac-rehearse
    python3 tv/preship.py --cheap          # fail-fast deterministic set
    python3 tv/preship.py --only agreement --root /path/to/worktree

A change to `.github/workflows` cannot be pushed from the box token; it has to go
out from the Mac.
