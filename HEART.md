# THE HEART — what watches the console

Derived by `tv/heart_map.py`. Do not edit by hand: it is regenerated on every bump and
the pre-push refuses when it is stale, exactly like BLUEPRINT.md.

A surface here is an `id` the console paints — the honest unit, because a class may be
shared by forty nodes while an id names one thing. WATCHED means the CODE of
`console_doctor.py`, `health_engine.py`, `corroborate.py` or `heart2.py` names it whole:
a comment or docstring naming it does not count, and a longer id (`th-shelf-x`) does not
vouch for its prefix (`th-shelf`). Before 2026-09-30 both did, and 13 of the console's 17
"watched" surfaces were named nowhere but in prose (REG-1555).

⚠ UNWATCHED IS NOT A DEFECT. Most surfaces neither need nor will ever have a watcher.
What is refused is a surface going unwatched SILENTLY — the count below is a ratchet and
may not fall without a human saying why in `heart_floor.json`.

| | |
|---|---|
| surfaces the console paints | **405** |
| of those, watched | **8** |
| coverage | **2.0%** |

## Watched

- `bug`
- `clock`
- `hero`
- `phase`
- `sadv-sha`
- `sadv-tip`
- `stage`
- `th-shelf-x`

## The board — `bible.html`

The page the console runs in its window: the builder, the 👤 Characters tab, the mule
window and the Vault paint their surfaces here. Same unit (an `id`), same watchers, its own
ratchet under `board` in `heart_floor.json`. Before 2026-09-29 this page was not mapped at
all, so its surfaces could be neither watched nor unwatched — only unsaid.

| | |
|---|---|
| surfaces the board paints | **602** |
| of those, watched | **4** |
| coverage | **0.7%** |

### Watched on the board

- `d2jsp-price-advanced`
- `d2jsp-price-backend`
- `inventory`
- `vault-moved-note`
