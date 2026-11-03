import { test, expect } from './_net_stub';
import * as path from 'path';
import { CALC_ITEMS_TOTAL } from './_data_locks';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v1716 — THE FARM BOARD WAS ROUTING OFF DATA THAT DID NOT COVER THE GAME.
//
// Konyo, on his own board: "for SETS i also see pindleskin as the runs... so thats definitely
// bugged.. + i see alot of UNVERIFIED boss hunts for farming which dont render anything at all."
//
// Both were true, and they were three separate defects:
//
//  1. SETS had no per-piece drop data at all — 14 "any piece" aggregate rows for 34 sets. The
//     picker maximises kph/chance and Pindleskin's kph (300-360) is 3-10x every other boss, so
//     the aggregate handed him TWO run cards, both Pindleskin, and 21 sets with no route.
//  2. The roster and the drop tables spell items differently. "Harlequin Crest" could not see
//     the row named "Harlequin Crest (Shako)", so the most farmed unique in the game rendered
//     as "no verified source yet" — 33 uniques sat in that bucket.
//  3. The tables were genuinely short: silospen RoW 3.0 lists 348 uniques for Hell Mephisto,
//     the tree carried 277.
//
// The 2026-08-16 silospen pull (D2R_ROW_3_0, MF=300, players=1, desecratedLevel 50/76/99 — the
// same convention the stored cells were pulled under: 230 of 243 overlapping Hell-Mephisto rows
// matched EXACTLY before anything was written) added 2,366 rows and re-synced 9,820 cells.
//
// What this spec pins is the OUTCOME on his board, not the pull.

const boot = async (page: any) => { await page.goto(URL); await page.waitForTimeout(2200); };

test.describe('v1716 — every hunt on the board resolves to a real run', () => {
  test('★ SETS route by PIECE, so the board is no longer one boss', async ({ page }) => {
    await boot(page);
    const r = await page.evaluate(() => {
      const w: any = window;
      const sets = w.__allSets ? w.__allSets() : [];
      let pieces = 0, routed = 0;
      const bosses = new Set<string>();
      for (const st of sets) {
        for (const pn of (st.pieces || [])) {
          pieces++;
          const s = w._pieceSrc(pn);
          if (s && s.boss) { routed++; bosses.add(String(s.bossId || s.boss)); }
        }
      }
      // distinct BOSSES, not distinct runs — a boss appears once per difficulty on the board,
      // so 3 bosses is 8 run cards. Both numbers matter and they are not the same number.
      return { sets: sets.length, pieces, routed, bosses: [...bosses] };
    });
    // the pull covers 134 of the 135 tracked pieces; a piece it does not cover falls back to the
    // set aggregate rather than to silence, so this floor is deliberately just under the total.
    expect(r.routed, 'set pieces with their own drop row').toBeGreaterThanOrEqual(r.pieces - 2);
    // THE BUG ITSELF: one boss answering for every set is what he saw.
    // Before: ONE boss (Pindleskin) answered for every set, because a single aggregate row per
    // set met a picker that maximises kph/chance. Any honest per-piece routing spreads. The
    // measured answer is 3 bosses across 8 run cards — Mephisto takes most of it because its set
    // odds really are ~10x Pindleskin's (Aldur's Advance 1:649 vs 1:7093), which is the DATA and
    // not a preference. Pinned at >1 because the defect was exactly 1.
    expect(r.bosses.length, 'distinct bosses across piece routes').toBeGreaterThan(1);
  });

  test('★ the F-SETS board ranks hardest-first, like the uniques board', async ({ page }) => {
    await boot(page);
    const diffs = await page.evaluate(() => {
      const w: any = window;
      w.switchTab && w.switchTab('fsets');
      w.renderForgeSets && w.renderForgeSets();
      const box = document.getElementById('fsets-body')!;
      // Read data-diff, NOT the prose. Regexing the card text for /Hell/ matched
      // "Run Normal TZ Hell Bovines" and scored a Normal run as Hell — the assertion then
      // failed on the instrument while the board was right. [[feedback-suspect-the-instrument]]
      return [...box.querySelectorAll('.f-card.f-pipe')]
        .map(c => c.getAttribute('data-diff'))
        .filter(v => v !== null && v !== '')
        .map(Number);
    });
    expect(diffs.length, 'run cards on the sets board').toBeGreaterThan(2);
    for (let i = 1; i < diffs.length; i++) {
      expect(diffs[i], 'run ' + (i + 1) + ' must not be harder than the run above it').toBeLessThanOrEqual(diffs[i - 1]);
    }
  });

  test('★ Harlequin Crest has a run again — and keeps the name he ticks', async ({ page }) => {
    await boot(page);
    const r = await page.evaluate(() => {
      const w: any = window;
      const fu = w.funiScan();
      const all = fu.missing.concat([]);
      const find = (n: string) => all.find((x: any) => x.n === n) || null;
      const shako = find('Harlequin Crest');
      const nosrc = fu.missing.filter((x: any) => !w._pickSrc(x.sources, x.n)).map((x: any) => x.n);
      return {
        shakoPresent: !!shako,
        shakoName: shako ? shako.n : null,
        shakoRouted: shako ? !!w._pickSrc(shako.sources, shako.n) : null,
        nosrc,
        found: fu.found,
      };
    });
    if (r.shakoPresent) {
      // the roster spelling is the LEDGER key — binding to the drop row must not rename it,
      // or a tick writes under a name nothing else reads (measured: 3 found uniques flipped
      // to missing the first time this returned the drop row itself).
      expect(r.shakoName, 'the roster name survives the bind').toBe('Harlequin Crest');
      expect(r.shakoRouted, 'Harlequin Crest resolves to a run').toBe(true);
    }
    // 33 before. What may honestly remain are items no boss drops: the six Sunder charms
    // (cubed), the Hellfire Torch (Uber Tristram) and Crescent Moon (two different uniques
    // share that name, so a single roster row cannot claim either one's odds).
    expect(r.nosrc.length, 'uniques with no tracked drop location: ' + r.nosrc.join(', ')).toBeLessThanOrEqual(10);
  });

  /* v1725 — THE EXAMPLE MOVED, THE PRINCIPLE DID NOT.
     This used to pin "Crescent Moon", on the belief that two different uniques carry that name.
     A fleet sweep proved otherwise: `Crescent Moon (sword)` was the RUNEWORD (ITEM_TIP carries
     `"t":"Runeword"` and the Shael+Um+Tir affix list — Ignore Target's Defense, -35% enemy
     lightning resist, Summon Spirit Wolf charges) sitting in ELEVEN boss drop tables as a
     farmable unique, with an ITEM_CODEX entry that called it a unique whose base is "Amulet" and
     whose props are byte-identical to the real amulet's. A runeword cannot drop. Removing it left
     ONE Crescent Moon, and it routes.
     The rule it was written for still holds and still needs a witness, so this now pins the real
     ambiguous pairs — an item and its redundant parenthetical twin. */
  test('★ a name with two rows does not borrow one row\'s route', async ({ page }) => {
    await boot(page);
    const r = await page.evaluate(() => {
      const w: any = window;
      const byKey: Record<string, string[]> = {};
      (w.ITEMS || []).forEach((x: any) => {
        const k = w._regKey(x.n); (byKey[k] = byKey[k] || []).push(x.n);
      });
      const dupes = Object.entries(byKey).filter(([, v]) => (v as string[]).length > 1);
      const cm = (w.ITEMS || []).filter((x: any) => /^Crescent Moon/.test(x.n)).map((x: any) => x.n);
      const miss = w.funiScan().missing.find((x: any) => x.n === 'Crescent Moon');
      return {
        dupeKeys: dupes.map(([k, v]) => k + ': ' + (v as string[]).join(' | ')),
        crescentRows: cm,
        crescentRouted: miss ? !!w._pickSrc(miss.sources, miss.n) : null,
      };
    });
    // the runeword is gone from the unique tables, so exactly one Crescent Moon remains
    expect(r.crescentRows, 'a runeword must not sit in the unique drop tables').toEqual(['Crescent Moon (amulet)']);
    if (r.crescentRouted !== null) {
      expect(r.crescentRouted, 'with one row it can finally be routed').toBe(true);
    }
    // the binding rule still has a subject: an item and its redundant twin
    expect(r.dupeKeys.length, 'no duplicate-key pair left to exercise the rule').toBeGreaterThan(0);
  });

  test('★ no item name is nc on one boss and not on another', async ({ page }) => {
    await boot(page);
    const r = await page.evaluate(() => (window as any)._ncAudit());
    // BOSSES is a module const, so the audit is published from inside its scope. A gate that
    // skips is a gate that does not run — this one must always have something to check.
    expect(r.checked, 'the nc audit could not read the drop tables: ' + (r.error || '')).toBeGreaterThan(300);
    expect(r.split, 'names flagged inconsistently: ' + r.split.join(', ')).toEqual([]);
  });

  /* The other half of the same seam: whatever a boss card RENDERS must be openable. This is the
     dead-click class v69 guards from the top-drops side; this one walks every rendered row. */
  test('★ every rendered boss drop row resolves in the calculator', async ({ page }) => {
    await boot(page);
    const r = await page.evaluate(() => {
      const w: any = window;
      const names = new Set((w.ITEMS || []).map((x: any) => x.n));
      const orphans: string[] = [];
      document.querySelectorAll('#boss-cards .boss-card table.drops tbody tr').forEach((tr: any) => {
        const n = tr.getAttribute('data-item') || '';
        if (n && !names.has(n)) orphans.push(n);
      });
      return { orphans: [...new Set(orphans)].slice(0, 20) };
    });
    expect(r.orphans, 'rendered rows with no calculator card: ' + r.orphans.join(', ')).toEqual([]);
  });

  /* v1720 — KONYO'S RULING: "add the 11 rotw items to the roster".
     v1716 found these in the RoW 3.0 tables; v1717 pulled their rows back out because the app had
     no card for them and a chip that opens nothing is worse than a drop he never sees. He then
     ruled them in. Each must now clear the whole bar v645 checks generically — in the roster,
     resolvable as a unique, carrying a real farm route and a picture — because a roster entry that
     cannot be opened or hunted is the defect this arc removed, not a new one to add. */
  test('★ the eleven he ruled in are real roster entries, not just names', async ({ page }) => {
    await boot(page);
    /* #165 — "CAN IT BE HUNTED" IS ASKED OF A BOARD THAT HAS NOT FOUND IT. Since REG-1275 a fresh board
       floors the seed like his, and five of the nine chronicle-counted names are seeded found, so they
       left the missing list and this read "not in the missing list (is it seeded found?)". Un-tick
       them through his own path (toggleOwned -> d2r_grailUnfound, which the floor respects) and ask
       again. Measured on a real page: 5 flipped, then all nine missing with a farm route. */
    await page.evaluate(() => {
      const w: any = window;
      ['Entropy Locket', "Hellwarden's Will", 'Measured Wrath', 'Opalvein', 'Sling', "Ars Al'Diabolos",
       "Ars Dul'Mephistos", "Ars Tor'Baalos", "Gheed's Wager"].forEach((n) => {
        if (w._gFound && w._gFound(n)) w.toggleOwned(n);
      });
    });
    await boot(page);
    const r = await page.evaluate(() => {
      const w: any = window;
      const N = ['Entropy Locket', "Hellwarden's Will", 'Latent Bone Break', 'Latent Flame Rift',
                 'Measured Wrath', 'Opalvein', 'Sling', "Ars Al'Diabolos", "Ars Dul'Mephistos",
                 "Ars Tor'Baalos", "Gheed's Wager"];
      const roster = new Set(w._gUniqueRoster());
      const fu = w.funiScan();
      const fail: string[] = [];
      /* ⚠⚠ v2705 — A LATENT SUNDER IS IN THE VAULT AND NOT IN THE CHRONICLE, BY HIS RULING.
         v2680, 2026-09-05: "for the chronicle all sunders 6 of them need to be counted in the
         chronicle specifically as 1 tally for each.. and for the vault that a different story the
         entire item database should be there regardless."
         So the roster (the vault's database) holds all six Latent forms and funiScan (a chronicle
         count) does not — which means `Latent Bone Break` and `Latent Flame Rift`, both in the
         eleven he ruled in back at v1720, can never appear in fu.missing again. This loop
         demanded exactly that and had been red since the ruling, reporting "not in the missing
         list (is it seeded found?)" — a question with a false premise: nothing seeded them, the
         chronicle simply does not count them any more.
         Every one of the eleven is still held to the VAULT half (in the roster, resolves as a
         unique, has art). Only the CHRONICLE half is scoped to the names the chronicle counts. */
      const LATENT = (x: string) => /^Latent /.test(x);
      N.forEach((n) => {
        if (!roster.has(n)) return fail.push(n + ': not in the roster');
        if (w.d2rResolveItem(n).kind !== 'unique') return fail.push(n + ': does not resolve as a unique');
        if (!w.artUrl(n)) return fail.push(n + ': no art');
        const it = fu.missing.find((x: any) => x.n === n);
        if (LATENT(n)) {
          /* the ruling, asserted from BOTH sides so a silent re-inclusion is caught too */
          if (it) return fail.push(n + ': a Latent sunder is back in the chronicle count — v2680 says one tally per sunder');
          return;
        }
        if (!it) return fail.push(n + ': not in the missing list (is it seeded found?)');
        if (!w._pickSrc(it.sources, n)) return fail.push(n + ': no farm route');
      });
      /* v2697 — REPORT THE INGREDIENTS, NOT JUST THE TOTAL. `rosterN` came back 392 against the
         398 asserted below, and from a bare total there is no way to tell WHICH side moved.
         _gUniqueRoster() is (ITEM_VALUE ∪ _UNI_EXTRA) − _pieces(), and that function reads no
         environment at all — no seeds, no ledger, no localStorage (verified by reading it with
         comments stripped). So a 6-name gap between his machine and CI has to come from one of
         these three inputs, and this line is the difference between naming it on the next run
         and guessing at it for another session. A total with no denominator is the defect this
         repo keeps paying for. */
      const ivKeys = Object.keys(w.ITEM_VALUE || {});
      const ueKeys = Object.keys(w._UNI_EXTRA || {});
      /* NAME the entries that did not survive into the roster, rather than reporting a total and
         leaving the next reader to subtract. _roster() is (ITEM_VALUE ∪ _UNI_EXTRA) − _pieces(),
         so anything present in an input and absent from the output was dropped as a set piece.
         This is arithmetic on OBSERVED values — it does not re-implement the exclusion rule,
         which would just be a second implementation free to disagree with the first. */
      const ueDropped = ueKeys.filter((n: string) => !roster.has(n));
      const ivDropped = ivKeys.filter((n: string) => !roster.has(n));
      const latent = ueKeys.filter((k: string) => /^Latent /.test(k));
      return { fail, rosterN: roster.size, found: fu.found, calcItems: (w.ITEMS || []).length,
               ivN: ivKeys.length, ueN: ueKeys.length, latent,
               ueDropped, ivDroppedN: ivDropped.length, ivDroppedSample: ivDropped.slice(0, 12),
               setsN: (w.__allSets ? Object.keys(w.__allSets() || {}).length : -1),
               missingN: (fu.missing || []).length };
    });
    /* printed unconditionally: when this test FAILS the message must already carry the numbers,
       because a failure that only says 392 sends the next reader back to re-run it for context. */
    console.log(`[v1716 roster inputs] ITEM_VALUE=${r.ivN} _UNI_EXTRA=${r.ueN} sets=${r.setsN} ` +
                `roster=${r.rosterN} missing=${r.missingN} found=${r.found}\n` +
                `[v1716 dropped]  from _UNI_EXTRA (${r.ueDropped.length}): ${r.ueDropped.join(', ') || '(none)'}\n` +
                `[v1716 dropped]  from ITEM_VALUE (${r.ivDroppedN}), first 12: ${r.ivDroppedSample.join(', ')}\n` +
                `[v1716 latent]   ${r.latent.length}: ${r.latent.join(', ')}`);
    expect(r.fail, 'roster entries that cannot be opened or hunted: ' + r.fail.join(' | ')).toEqual([]);
    // v3859 — 398 → 396: his ruling removed the fake "Polaris Spear" and folded "The Scourge" into Stormlash.
    expect(r.rosterN, 'the roster must have grown by exactly the eleven (less the two v3859 removals)').toBe(396);
    /* he ruled on the ROSTER. The curated calculator grid is a different surface and stays put.
       v1724 — this used to hard-code 322, so removing one garbled row (Bloodmoon's Light) made a
       guard about the ROSTER fail over the CALCULATOR's count. Read the single definition instead
       of keeping a second copy of the number. */
    expect(r.calcItems, 'the calculator is not what he ruled on').toBe(CALC_ITEMS_TOTAL);
  });
});
