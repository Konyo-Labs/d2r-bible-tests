# GROK_REPORT_K

Worktree `/private/tmp/grok-v3849k`, branch `grok/v3849-k`. Commit only. No push. `tv/run_gates.py` was not executed. No other worktree, and no extra Mac proof job.

## What landed

Dean stays the ALT's first prover. Konyo (the Mac) is the backup. `PROOF_CARRIER_ACCEPTS["Konyo · ALT"]` is `("Dean", "Konyo")`. The first peer whose export is at this HEAD and still fresh is imported, and the rest are not asked. `PROOF_CARRIER_FRESH_S` is `26 * 3600`. Missing, UNKNOWN, clock-ahead, another HEAD, and a refused import fall through. Both peers missing or stale imports nobody.

`PROOF_CARRIER_PLATFORMS` stays `("win32",)`. darwin publishes and never takes. The Mac publishes only when `gate_run_kind` for this HEAD is `"pre-push"` or `"nightly"`. The pre-push hook notes a successful `heart2 --prove`. The nightly notes a full run whose exit code is 0. A proof job does not note itself, and the carrier's publish path is `heart2 --export-proved`.

Proof keys digest LF-normalised text in both `_sha_file` and the stamp-masked hasher. A NUL file is hashed as stored. A lone CR still differs. An entry the byte check drops is not banked and not marked carried. The ALT asks the route for `Konyo · Mac` and records the carrier as `Konyo`.

The older carried-proof law's peer assertion and its red-proof anchor follow the new accepts line. Roster owners and the proofs route were not edited.

## Laws

Each law was run on its own, then each red-proof on its own. After every red-proof the diff was the same as before it.

- `tv/test_alt_falls_back_to_the_mac_when_dean_is_stale.py` — 8 tests OK. 5 red-proofs PROVEN.
- `tv/test_a_cross_os_proof_carries_only_on_identical_normalised_bytes.py` — 2 tests OK. 5 red-proofs PROVEN.
- `tv/test_the_mac_publishes_only_from_a_gate_run_it_already_did.py` — 4 tests OK. 6 red-proofs PROVEN.

Gates are registered immediately after `test_esc_clears_a_typed_lookup_over_an_overlay`.

## Not taken

darwin was not added to the take-platform tuple. The self-prove tick was not widened to the Mac. No proof is forged when both peers are stale or missing.
