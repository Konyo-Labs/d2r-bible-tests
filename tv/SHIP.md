# Shipping a version

One entry point:

    python3 tv/ship.py vNNNN

`tv/ship_when_green.py` is the engine; `tv/ship.py` turns the system on and prints the
per-round report. Never `--no-verify` on main, never a force push to main, never a
token in the output. Main moves only through `hooks/pre-push`.

## The flow

1. **Box rehearsal** (`tv/preship.py`) — every gate that does not depend on the Mac:
   encoding-safe, swallow census, agreement laws (a law that pins a gate number must
   agree with that gate; attempt 7), the exact tests of any shard that failed in the
   last N rounds (attempt 9: agent-suite (2) / `test_the_planner_spinner_stays_under_the_cursor`;
   a cut-off shard is rehearsed as the same `k/n` slice), blueprint, heart map,
   render_check (all targets, all five viewports), console-demos via
   `node tv/demo_console.mjs`, and the agent tests this push touches. Cheap
   deterministic checks run first. A red **blocks the ci/ push**.
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
5. **Live shard watch, then make-up** — during the CI wait the engine watches
   per-job status (every 20s while a required suite is in progress). The moment
   one shard goes red it pulls that job's log and classifies it: a real test
   failure is reported immediately so the fix can start while other shards are
   still running; a flake, runner cut-off, timeout, or infra kill is auto-rerun
   with `gh run rerun --failed` (or queued until the run completes, because
   GitHub refuses a mid-run rerun). Proof-keys shards still use REG-3270. A
   healed flake drops out after 3 clean runs. Required-check judgement looks only at required jobs (the Linux seed, the ci shard jobs, and the fan-in that bags them). Non-required proof-keys windows jobs never hold the wait, and they do not trip the 75-minute alert on their own (attempt 10, REG-3652). While a real ship (ci/claude-* or ci/proof-keys-*) is live, or a Publish run on main is queued or in progress, or in the window after a main push until Publish finishes, dry/ and grok/ CI pushes yield: they are not launched, and already-running ones are cancelled so a ship's or Publish's jobs never wait on our own test runners (attempt 10, REG-3653; v3893 Publish, REG-3654). If a ship or Publish has been queued more than about two minutes while our own dry/, grok/, or ci/*dry* runs hold runners, the ship script cancels those runs itself (never main, never the live ship's required jobs) and names lesson bundle-v3893-publish-queued. A sweeper cancels leftover dry runs on superseded shas and anything on a ci/*dry* name, which must never be used again. A shard that fails twice in three
   rounds, or that runs near the 25-minute ceiling (under 300s left), is flagged
   to split; `choose_shards` then asks for one extra slice (capped at SHARD_MAX)
   and the flag lists the slow or failing tests to move.
6. **Main**, through `hooks/pre-push` (the hook trusts GitHub's verdict and runs what
   GitHub cannot). The hook also re-checks Mac readiness as a backstop.
7. **Post-land** — watch Publish (and keep yielding dry/grok runners to it, REG-3654); ask the live console's `/api/status` whether it
   names this version (a silent console is said, not a refusal).

## Self-improvement

- `tv/preship_lessons.json` — every ship refusal that a cheap check could have caught,
  plus the check that now catches it. A shard failure records the shard's identity
  (attempt 9: `agent-suite (2)`) so a repeat is caught before the next push.
  Adding a lesson is one entry; the law
  `test_every_preship_lesson_names_a_check_that_runs` refuses a check that does not
  exist or is not run. Seeded with bundle attempts 6, 7, 8 and 9. A new preship
  refusal is appended automatically.
- `tv/shard_history.json` — last N rounds of agent-suite / Playwright shard
  outcomes, plus split flags. The box rehearsal reads it (REG-3647); the live
  watch writes it (REG-3648); a 2-of-3 or near-ceiling flag is REG-3649.
- `tv/shard_timings.json` — a row for every proof test, measured when a green
  proof-keys round has measured it, otherwise the median. The plan uses these rows
  to fill unpriced proofs. Updated after a green round. Law:
  `test_the_shard_balance_file_covers_every_proof_test`.
- `baseline/integrity_baseline.json` — Routine L's ITEMS/BOSSES counts. The box rehearsal's `integrity` check runs the same probe so a drift is caught before CI (REG-3651).
- `tv/flake_ledger.json` — known flakes, pruned after `nClean` (3) consecutive
  green runs.

## Time saved

Attempts 6, 7 and 8 each paid a full GitHub round (~60 minutes; the v3864 proof
shards alone ran 43–87 minutes, REG-3213 / ci_speed) before the Mac hook, or the
agreement law, refused. A local red now costs minutes. A flaky agent or Playwright
job re-runs only that job, not the green shards of the same workflow. A real
red shard is reported as soon as that job finishes, not after the rest of the
round (attempt 9 waited on the whole suite, then VERDICT, for a law that had
already failed).

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
