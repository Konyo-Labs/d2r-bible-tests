# D2R Bible — Game Rules & Facts (RoW canonical reference)

> **Living knowledge base.** The durable, game-truth facts the app encodes — so any
> agent (Claude Code, Claude Desktop) can build on a solid foundation without
> re-deriving the rules. Konyo plays **Reign of the Warlock (RoW / ROTW)**, NOT
> vanilla D2R. Sources: diablo2.io, Maxroll, silospen, in-game. **ZERO fabrication** —
> if a number isn't sourced, it's marked qualitative, never invented.
>
> Companion docs: `BUILD_LOG.md` (what shipped, dated), `BUGS.md` (regression log).

## Tabs / structure of bible.html
- Single-file HTML app. Top-level tabs: bosses, calc, tz, runes, rotw, ancients
  (events/uber), endgame (storyline "Road to the Hellfire Torch"), reference, binds.
- Central routers: `openDrop(name)` resolves a drop → its card
  (findHeraldTier → findRune → findMaterial → ITEMS); `switchTab(id)`;
  `artOr(name, fallbackHtml, size)` art helper (lg/sm). **Site-wide blast radius.**

---

## RoW endgame — the Colossal Ancients chain (pinnacle)

### Colossal Statues (cube material)
Five element-themed statues, each drops from a **TERRORIZED Hell act boss only**
(~1:8 to 1:15 per kill; **MF does NOT affect**; never drops un-terrorized):
| Statue | Drops from (terrorized Hell) |
|---|---|
| Talic's Anguish | Andariel |
| Korlic's Pain | Duriel |
| Madawc's Ire | Mephisto |
| Bul-Kathos' Nightmare | Diablo |
| Worusk's End | Baal |
Cube all 5 → **Colossal Summit** → Act 5 red portal → summon the **Colossal Ancients**.
Statues carry no equip stats — pure cube ingredient gating the whole RoW endgame.

### Colossal Ancients (the 3 bosses)
Buffed Ancient Barbarians; re-roll stats + **one random immunity each game** (like
vanilla Ancients — leave+remake to re-roll if all three share an unbreakable immunity).
mlvl Colossal (drop lvl-75 jewels), massively buffed HP/def. You receive the jewel
matching the Ancient you kill **LAST**.
| Ancient | Weapon / style | Drops (by last kill) |
|---|---|---|
| Talic | sword & shield · Whirlwind | Defender's Fire (fire) / Defender's Bile (poison) |
| Korlic | polearm · Leap Attack | Protector's Frost (cold) / Protector's Stone (physical) |
| Madawc | dual throwing axes · caster | Guardian's Thunder (lightning) / Guardian's Light (magic) |

### Colossal Ancient Jewels (endgame BiS — strictly better than Rainbow Facets)
ilvl 75. **1 per character** (you keep the one matching the last Ancient killed).
**Every** jewel shares: 1% chance-to-cast its element armor when struck · +its element
damage · +5-10% to that skill-damage type · -5-10% to enemy element resistance ·
+3-5% experience · +25-50% extra gold · +15-35% magic find.
| Jewel | Element | CtC armor (lvl) | +element damage |
|---|---|---|---|
| Defender's Bile | poison | Bone Armor (25) | +95 poison over 1s |
| Guardian's Thunder | lightning | Cyclone Armor (25) | +1-75 lightning |
| Protector's Frost | cold | Frozen Armor (25) | +10-30 cold |
| Defender's Fire | fire | Blaze (25) | +20-60 fire |
| Protector's Stone | physical | Fade (15) | +30-50% ED, +10-30 (min/max) · -5-10% enemy phys-dmg reduction |
| Guardian's Light | magic | Psychic Ward (25) | +15-35 magic |
(Protector's Stone is the physical variant: enhanced damage + flat damage instead of
+skill%, and its "enemy res" line is -enemy physical damage reduction.)

---

## Herald of Terror & Sunder Charms (RoW immunity-breaking)

### Herald ladder (5 Hell-TZ superunique rungs)
Spawn only in **Hell Terror Zones**. Two-step hidden token system:
1. **Draw its ire (~2%)** — every Champion/Unique/Superunique/Boss killed in the active
   Hell TZ has ~2% to bank a token ("You have drawn the ire of a Herald!"). Stacks ×5.
2. **Let it hunt you (~1%)** — while holding a token, each monster spawned on a fresh
   unexplored tile has ~1% to become a Herald. Reveal new ground, don't grind.
Each kill bumps the **next** Herald one tier: Fright → Dread → Fear → Horror → **Terror**.
Tiers reset to Fright if you exit to main menu. Once at Terror, all stay Terror that session.
Worldstone-Shard method: pop a shard to terrorize a whole act for continuous fresh tiles.
- **Herald of Terror** (apex) is the prime Sunder source — has a dedicated rich RotW ID
  card (`#herald-card`). All "Herald of Terror" routes funnel to it (`openHeraldCard()`);
  the 4 lower rungs use lean tier cards.

### The 6 Latent Sunder Charms (grand charms — each breaks ONE immunity to ~95%)
Drop from any Terror-Zone monster, Heralds most often. Every Sunder can be worn at once; a second copy of the same charm only stacks its penalty. Hell only.
| Charm | Breaks | Best for (Konyo's build) | Renewed upgrade |
|---|---|---|---|
| Bone Break | physical | Konyolock (phys Assassin) | + Perf Amethyst + Pul + Northern shard |
| Black Cleft | magic | Konyodin (Hammerdin) | + Perf Diamond + Mal + Southern/Deep/Northern shards |
| Crack of the Heavens | lightning | Konyoress (light sorc) | + Perf Topaz + Fal + Southern shard |
| Cold Rupture | cold | Frozen Orb/Blizzard sorc | + Perf Sapphire + Lum + Eastern shard |
| Flame Rift | fire | Fireball/Meteor sorc | + Perf Ruby + Io + Deep shard |
| Rotting Fissure | poison | Poison Necromancer | + Perf Emerald + Ko + Western shard |
Renewed recipe (per charm): Latent Sunder + Perfect Gem + Rune + that charm's shard count. Five charms take one named shard, and Black Cleft takes three: Southern + Deep + Northern. Source: Maxroll.

### Worldstone Shards (upgrade a Latent → Renewed Sunder; MF does NOT affect, ~1:500-1500)
Western=Act1 zones, Eastern=Act2, Southern=Act3, Deep=Act4, Northern=Act5.

---

## Pandemonium / Uber Tristram chain (→ Hellfire Torch)
- 3 Pandemonium keys (Terror=Hell Countess, Hate=Hell Summoner/Arcane Sanctuary,
  Destruction=Hell Nihlathak/Halls of Vaught), ~10% Hell /p3+. Cube 1 of each →
  one **random** mini-uber portal.
- 3 mini-ubers drop the 3 organs (100%/kill): Lilith→Diablo's Horn,
  Uber Izual→Mephisto's Brain, Uber Duriel→Baal's Eye. Cube 3 organs → Uber Tristram.
- Uber Tristram trio (Uber Meph/Diablo/Baal) → Standard of Heroes → **Hellfire Torch**
  (+3 random class skills, +10-20 all res, +10 all stats; 1 per character).
- **Diablo Clone (Über Diablo)** side-path: triggered by mass SoJ sales → drops **Annihilus**.

---

## Logging / TDD discipline (carried from the Kai/Achilles golden suite)
- **Every feature ships with a Playwright TDD spec** (write/extend the spec, confirm
  the assertion, then keep it green). Specs live in `tests/vNN_*.spec.ts`.
- **Every regression** → `BUGS.md` as `REG-NNN`: symptom · caught-by · root cause ·
  fix · prevention.
- **Every build session / decision** → dated `BUILD_LOG.md` entry.
- **Durable game facts** → here (`GAME_RULES.md`).
- Maintained continuously by CC's Obsidian logging loop (every ~2h).

---

## Drop-odds architecture & data provenance (how the numbers are derived)
> The single most important "don't re-derive this" fact. ZERO fabrication: every
> odds cell traces to a source below; un-sourced numbers are marked qualitative.

- `BOSSES[].dropTable` (JSON, ~line 2638) holds the FULL TC-reachable grail pool
  per boss (every reachable row, NOT a curated top-N). The calc grid reads it live, and so
  should you — the per-boss row count varies by boss and moves with every data pull.
- **RoW, not vanilla.** Konyo plays Reign of the Warlock. All unique/set rows were
  repulled from silospen's live JSON API (`dropcalc.silospen.com/dropcalc.php`,
  `version=D2R_ROW_3_0`, query `monsterProbabilities`, **MF=300, players=1** — that
  combo matches the bible's stored-base reference). Commit `13f8e94` rewrote 1,975
  rows across 8 farmable bosses.
- **RoW anchors (verified cells — update `tests/02_verified_anchors.spec.ts` if these
  ever change):** Meph/Hell/Shako **1:836** · NM Anda/SoJ **1:2,286** · Hell Anda/BK
  **1:4,080**. (Old vanilla values 912 / 1,617 / 2,721 are SUPERSEDED.)
- Per-boss act-boss/minion odds = Mephisto's rarity column × one constant scalar
  (proven by median=min ratio); only Countess/Travincal/Cows/Pit got per-item tuning.
- **RoW-calibrated since:** the 8 boss TZ columns (v129/v187) · **Travincal Council +
  Hell Bovines FULL base+TZ (v697, 2026-07-15: 2,245 cells; council = 3 SUs combined
  1/(Σ1/Nᵢ); REGULAR ids keep their PLAIN id under `desecrated=true` — d-suffix is
  boss/SU only)**.
- **v700 additions:** all 11 TZ zone cards carry per-kill DWELLER odds (silospen location-verified;
  dweller map in commit 7768873); the hunt grids route to them. **Odds-honesty state: COMPLETE** —
  every boss/SU/zone/area = RoW truth or an explicit label (Colossal/materials/Heralds stay
  community-estimate labeled until primary sources exist).
- **v699 additions:** Pit = per-kill of a Pit Level 1 dweller (1,033 cells) · council rune grid EXACT (Zod is TZ-ONLY: 1:97,811) ·
  ⚠ **REG-2954 (2026-10-29):** the dweller is a MELEE one — `fallen3` (Devilkin); `skeleton3` (Bone Warrior) is
  identical and `corruptrogue3` (Dark Stalker) too except on Normal. It was written down as `cr_archer3` (Dark Archer),
  which is the odd one out: levels.txt gives Pit Level 1 four monster types (skeleton3, fallen3, corruptrogue3,
  cr_archer3), and monstats/TreasureClassEx put the archer on the `Miss` table (Equip 13 of 160) where the other three
  roll `H2H` (Equip 16 of 160) - so an archer kill is 13/16 of the stored odds on non-bow items. The stored Nightmare
  column had been pulled from Pit Level 2 (area level 40 vs 39); it is Pit Level 1 now. Sources: silospen
  D2R_ROW_3_0 monsterProbabilities (fallen3, area Pit Level 1); @blizzhackers/d2data 3.1.91636 (D2R CASC tables,
  2026-02-12) levels.json / monstats.json / treasureclassex.json ·
  14 super-uniques carry per-kill odds (su-odds-data).
- **Fixed-rate mechanics (not silospen-modelable, community-verified):** Key of Hate 36%
  per Summoner kill · Annihilus per-DClone. Countess rune odds separately calibrated (1:850 Ist).
- **Materials are NOT MF-scaled and NOT in the tracked grail count** (sunders,
  shards, statues, jewels, keys, organs, essences). Their per-kill figures are
  community estimates (silospen / d2runewizard / diablo2.io / Maxroll), never invented.
- **Integrity gate** = `baseline/integrity_baseline.json` probes (item count, 13 bosses,
  drop probes) checked by `routine-l-integrity.yml` — NOT a file md5 hash. UI-only
  edits that don't touch BOSSES data stay green.
  ⚠ **Do not restate the item count in this file.** It has drifted three times (312 → 322 → 320)
  and this sentence carried the stale value every time. `tests/_data_locks.ts` is the ONE
  definition; every spec imports it and the baseline is generated, never typed.
  Baseline mirrors anchors (e.g. `probe_meph_shako.hell` = 836).

## Live deploy + CI (cost-free; no AWS/Achilles)
- Live: `https://bull-4-u.com/d2r/` — Cloudflare **Pages** project `d2r-bible`
  (free tier), serves `d2r-bible.pages.dev`; apex `/` → 302 → `/d2r/` via `_redirects`.
- Deploy is **MANUAL direct-upload** (project `source: None` — a `git push` does NOT
  build the site). **Since v231 the art is self-hosted, so the dist must include `art/`:**
  `cp bible.html /tmp/d2r_dist/d2r/index.html` (single-line!) then
  `rm -rf /tmp/d2r_dist/d2r/art && cp -R art /tmp/d2r_dist/d2r/art` then
  `cd /tmp/d2r_dist && set -a && . ~/.config/cf-d2r/env && set +a && npx wrangler@latest
  pages deploy . --project-name=d2r-bible --branch=main`. Then verify md5 parity:
  `curl -s -A 'Mozilla/5.0' https://bull-4-u.com/d2r/ | md5 -q` == `md5 -q bible.html`,
  and a sample `https://bull-4-u.com/d2r/art/madawcs_ire_graphic.png` → `200 image/png`.
- Edge does NOT cache HTML (`cf-cache-status: DYNAMIC`) — a stale view is the user's
  browser cache (⌘⇧R fixes it).
- Repo `KonyoDigital/d2r-bible-tests` is **PUBLIC** → free/unlimited GitHub Actions
  (all routines run free). Konyo will not pay for CI. If a billing-block annotation
  reappears, confirm the repo is still public (it's account-level, not a code regression).
- Pre-push hook (`core.hooksPath=hooks`) runs a smoke gate
  (`01_smoke + v71_d2art + v74_material_search + v80_endgame_relics`) before pushes
  touching `bible.html`/specs. CI (Routine I) is the BACKSTOP, not the gate.
