# THE GROK GUEST SEAT — refresh it from live, and stage a recorded run

Grok Bot's eyes drive TV DIABLO on **the box** at `http://127.0.0.1:18772/`, against a
**read-only mirror** of Konyo's live console. No Mac mouse, ever.

---

## The one command

On the **Mac**, with the live console running on `:17772`:

```bash
bash tv/sync_guest_api.sh            # pull live -> ./guest-mirror/  (+ restage every fixture pack)
bash tv/sync_guest_api.sh --to-box   # ...and rsync it to the box
```

`--to-box` needs a destination:

```bash
GUEST_BOX_HOST=box bash tv/sync_guest_api.sh --to-box
# override the path with GUEST_BOX_PATH (default /workspace/tv-diablo-guest/api-live)
```

**What a run does, in order:** mirrors the read-only endpoints → scrubs every one → scrubs the
6.4 MB board HTML → restages every fixture pack → runs the leak gate → checks every picture the
board and the console can ask `/art/` for (`tv/art_names.py`) → only then copies, **art included**.

**The art travels with the board (REG-3206).** A refresh used to ship a new board and never the
pictures it names, so the guest kept an older art tree than its board (~103 distinct `/art/*` 404s
measured at v3864). `--to-box` now rsyncs the repo's `art/` to `GUEST_BOX_ART` (default
`$GUEST_BOX_PATH/art`); point that at wherever the box's bridge serves `/art/` from.

**A guest never asks `/api/update` (REG-3207).** `update` is not mirrored, and the mirrored
`/api/status` says `guest: true`; the console reads that and does not ask.

**It refuses to copy a mirror that still carries his machine.** On the first ever run the raw
board came back with four of his identifiers and the copy was aborted. That gate is the reason
this is safe to point at a public issue.

---

## What is deliberately NOT mirrored

`board_tick` · `chronicle_apply` · `vault_apply` · `vault_forget` · `session/delete` ·
`relaunch` · `restart` · `quit` · `update` · `on` / `off` / `stop`

The mirror is read-only **by allowlist**, not by intention, and
`test_the_guest_seat_is_grok_not_konyo` fails if a write door is ever added. An eyes-loop must
never be able to change what he owns.

---

## Staging one of his recorded runs

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, 'tv')
import guest_fixture_pack as fx
fx.build('tv/frames/hist/reel_<sid>', 'pack-<name>',
         title='what it shows', why='why it is worth clicking')
PY
bash tv/sync_guest_api.sh            # the pack is restaged on every refresh from here on
```

A pack is **versioned, checksummed and self-describing** (`fixtures/<pack-id>/pack.json`), and
carries a representative subset rather than the reel: measured, **196 MB / 153 frames → 2.7 MB /
16**, evenly spaced so the scrub bar still travels the whole run.

**Every staged session declares itself** — `fixture: true`, its `fixturePack`, and a
`footageWhy` saying the frames it lacks were *never copied*, not pruned. A fixture that cannot be
told from his real footage would have an eyes-loop reporting findings about staged data as if
they were his.

`load()` **refuses** any destination under `tv/frames`. A pack may be BUILT from his footage and
never LOADED into it — footage has no un-delete.

---

## Neither directory is ever committed

`guest-mirror/` and `fixtures/` are gitignored. They hold his ledger, his 419 sessions and actual
frames of his game. The scrub removes his machine's *identifiers*; it does not make his *data*
publishable, and **this repo is public**. They travel to the box by rsync.

---

## The guest board reads 0/135 — that is the safety rule, not a bug

`bible.html` decides which world a machine gets with one line:

```js
var m = /mac|iphone|ipad|ipod/i.test(plat) ? 'mac' : 'windows';
```

**Linux falls to `windows`**, gets the isolated cousin world and starts from zero. The ribbon says
"WINDOWS" on a Linux box for the same reason — it is the label for *not-Mac*. The code states the
reasoning: *"a machine wrongly placed in its OWN world sees an empty console, while a machine
wrongly placed in the OWNER's world sees someone else's chronicle."* Empty is the safe side.

⚠ **Do not "fix" this by claiming the mac world.** Setting `d2r_activeMachine=mac` is exactly the
failure the rule exists to prevent, and the guest is the one seat that must never be able to write
into his namespace.

**Fill it instead.** Every refresh writes `guest-mirror/seed_progress.json` in the board's own
`exportProgress` schema (v2, flat bare-named stores — `_applyProgress` routes them into whichever
world is active, so they land in the cousin world by construction). On the guest board:

> **Tools → Backup → paste `seed_progress.json` → Import**

Measured on the current backup: **81 stores, 172 owned items**, scrubbed. His Mac is untouched —
the worlds are separate keyspaces inside *that* browser's storage.

---

## Making the seat show up as **Grok** in THE FLEET

Consoles appear online by beaconing with their hostname. Grok Bot's machine is already in the
fleet — as the bare hostname, because it has no nickname. On **that machine's own console**
(`:17772`, not the guest bridge on `:18772`):

```bash
curl -X POST http://127.0.0.1:17772/api/identity_name \
  -H 'Content-Type: application/json' -d '{"name":"Grok"}'
```

It re-beacons immediately and renders beside Konyo and Dean.

⚠ A fleet row reading **"no report · no board window"** is not a sync failure. That console can
COUNT its pieces but cannot NAME them until a board window is open — which is what the mirror's
scrubbed `board.html` is for. Dean's row says the same thing for the same reason.
