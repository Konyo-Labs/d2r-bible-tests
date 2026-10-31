# GROK_REPORT_F

Worktree `/private/tmp/grok-v3849f`, branch `grok/v3849-f`. No push. `tv/CHANGELOG.json` was not edited. `tv/run_gates.py`, heart2, and Chrome were not run.

## Changelog

- v3849 - shadow bar: LEAVE SHADOW close-chip, bigger Their sessions, Esc leaves only when no overlay is open
- v3849 - a 30-item d2jsp fixture batch prices each item or says none close, and every post keeps its forum link
- v3849 - a no-roll price 10x off the close-fit median is one quiet "n lines skipped"; a weak key mod never weighs 1.00
- v3849 - a fresh d2jsp price refresh says "paused while checks run" and does not fetch while gates run

## Commits

- C1: no new commit. The law was already on this branch (`tv/test_esc_leaves_a_shadow_only_when_nothing_is_open.py`, last touched by `1f34332f6`). This session did not edit it and did not re-run it.
- F1 `5a58bf1ee` — v3849: a 30-item d2jsp fixture batch prices each item or says none close
- F2 `40a1e6f27` — v3849: a no-roll price 10x off the close fit is one quiet skip
- F3 `b52a43873` — v3849: a fresh d2jsp price refresh pauses while checks run

`792f6cfb7` (grok/v3849-side) was not an ancestor and was not cherry-picked. Its 30-post Shako / Annihilus / Guardian's Thunder assertions were rewritten into the F1 law (node on stdin, `encoding="utf-8"`). Its `run_gates.py` hunk and `GROK_REPORT.md` were not taken. The law extends that batch to 30 items from fixtures only.

## Laws

- C1 `tv/test_esc_leaves_a_shadow_only_when_nothing_is_open.py`, gate already before the rerun anchor. Esc leaves a shadow only when the overlay stack is empty. LEAVE SHADOW uses the overlay-close chip.
- F1 `tv/test_d2jsp_30_item_batch_e2e.py`. 30 fixture items, no network. Each item is a price headline or the words `none close`. Every post keeps a `forums.d2jsp.org` link. The 30-post batch rides along (9000 fg Shako set aside, Annihilus 15/15/5 set aside, Guardian's Thunder key-mod fit).
- F2 `tv/test_d2jsp_gross_outlier_and_key_weight.py`.
- F3 `tv/test_a_price_refresh_pauses_while_checks_run.py`.

F2 gates were inserted immediately before `test_a_rerun_runs_only_the_last_reds`, after F1. F3 sits after F2.

## F2 audit

- Links carried per post: already guarded by `tv/test_the_d2jsp_price_search_shows_its_posts_and_weighs_the_key_mods.py::test_each_post_carries_its_link_day_and_roll`. F1 also asserts every post in the 30-item batch. Not reimplemented.
- Gross-outlier skip: was missing. A post with no roll, and at least three rolled posts, is set aside when it is over 10x or under 0.1x that close-fit median. Weight 0, no new loud reason. The price line gains one `1 line skipped.` or `N lines skipped.` The 3x "far from the middle" rule is unchanged. The 9000 fg Shako (no close-fit roll) still uses that loud rule.
- Key-mod weight: family keys and a key the posts priced still may weigh 1.00 (`learned` stays `[1, 0]`). A mod with no family weighs 0.25 and the tier line says `no key-mod family to weigh`. An unreadable column is weight 0 with drawer reason `key mods could not be read`. A column fit with no key mod is capped at 0.25. An affix line that matches no row stays in the drawer as `Check: could not be read.` and is not weighed.
- Perfect-roll tier: already guarded by `tv/test_the_d2jsp_price_db_ages_weighs_and_merges.py::test_a_perfect_post_never_lifts_the_normal_price` and `test_the_quote_door_folds_the_reading_and_the_parser_carries_perfect`.
- Fleet sync merge: already guarded by `test_two_pcs_merge_into_one_db_either_way` in that same law.

## Red-proofs

Each proof was applied alone, the law exited 1, and the file was restored. Then the law was run green.

F1, 8 tests OK after restore. While sabotaged:

- 3x check forced false: Shako came back `(145, 10, 100, 9000)` and the 9000 fg post kept its weight.
- Relative forum link returned empty: both link tests saw `link: ''`.
- Similar-price always set `fg`: the five none-close items came back as a price headline.

F2, 9 tests OK. F1 was re-run after the F2 production edit and stayed 8 tests OK. While sabotaged:

- 10x check forced false: the five-line and one-line skip tests failed.
- Price-line skip suffix forced off: those same two tests failed.
- Public door dropped `skipped`: those same two tests failed.
- Even fallback returned weight 1: the no-family test and the unreadable-column test failed.
- Unreadable column went back to weight 0.05 with no reason: the drawer test failed.
- No-key cap removed: the column rows weighed 1.00 and that test failed.
- Unparsed affix dropped again: `Check: could not be read.` was gone.

F3, 9 tests OK. While sabotaged:

- `if busy is None or busy` forced false: the lanes, held-lock, unreadable-lock, busy-why, and why-raising tests all fetched.
- Heart2 lanes check forced false: `test_heart2_lanes_pause_and_do_not_fetch` fetched.
- `if held` forced false: `test_a_held_gate_lock_pauses` fetched.
- Unreadable lock returned free: `test_an_unreadable_lock_does_not_fetch` got `say is None`.
- Free lock returned busy: `test_when_the_lock_is_free_only_the_stale_item_is_fetched` paused.
- `if sentence` forced false: `test_a_busy_why_pauses_without_fetching` fetched.
- `why()` raising returned free: `test_why_raising_does_not_fetch` fetched.
- Quote door `checks_running()` check forced false: `test_the_quote_door_says_paused_before_it_fetches` errored.

The pause is `paused while checks run`. `HEART2_LANES` other than `"0"`, a held `D2R_GATE_LOCK_KEY` flock, and `tree_busy.why()` (busy or raising) all refuse the fetch. A private env whose lock is free does not ask the live pre-push. Unknown is not free. The `/api/d2jsp_quote` handler returns that sentence before `d2jsp_quote`.

## Open

- C1 in the order stops at "A partial ea". Nothing after that fragment was specified, so nothing further was built.
- Vault bug refs were given as none.
