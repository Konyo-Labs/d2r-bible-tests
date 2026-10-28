import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v1616.1 — MF-BLINDNESS IS A QUESTION ABOUT ITEM CLASS, NOT ABOUT SPELLING.
//
// v1616 taught the chronicles to respect the MF and /players sliders, and gated the MF half behind
// a predicate that regex'd the item's NAME for "rune|gem|jewel|charm|gold". Its own test probed the
// strings "Perfect gem" and "Sunder charm" — both contain a class word, neither is an item — so it
// went green while every real member of those classes was being MF-scaled:
//
//     Perfect Ruby      1:7,727 -> 1:4,293 on the drag      no gem is called "gem"
//     Gheed's Fortune   MF-scaled                           no charm is called "charm"
//     Annihilus         MF-scaled                           both are in his grail
//
// and the mirror is one character away: "Rune Bow" and "Rune Sword" are WEAPON bases, so Magewrath
// and Plague Bearer are ordinary uniques that MUST keep scaling. A substring match is wrong in both
// directions, so the predicate now reads ITEM_CODEX.base plus the app's own GEM_TYPES / RUNES /
// SUNDER_CHARMS vocabularies.
//
// EVERY NAME BELOW IS A REAL ITEM. That is the whole point of this file: the previous test could
// not have caught this, because it never asked about anything that exists.

test('\u2605\u2605\u2605 the sliders move exactly what they should, by CLASS', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(2600);
  const probe = await page.evaluate(() => {
    const w: any = window;
    const set = (mf: number, pl: number) => {
      const m: any = document.getElementById('mf'), p: any = document.getElementById('players');
      m.value = String(mf); m.dispatchEvent(new Event('input', { bubbles: true }));
      p.value = String(pl); p.dispatchEvent(new Event('input', { bubbles: true }));
    };
    const c = (chance: number, boss: string, diff: string, name: string) =>
      w._fAdjC({ chance, bossId: boss, diffKey: diff }, name);
    const out: any = {};
    // a real unique off Hell Mephisto
    set(0, 1);   out.uni_mf0    = c(5000, 'mephisto', 'hell', 'Frostburn');
    set(1000, 1); out.uni_mf1000 = c(5000, 'mephisto', 'hell', 'Frostburn');
    // MF-blind classes at the same two MF values
    set(0, 1);   out.rune_mf0 = c(5000, 'mephisto', 'hell', 'Ist Rune');
    set(1000, 1); out.rune_mf1000 = c(5000, 'mephisto', 'hell', 'Ist Rune');
    set(0, 1);   out.gem_mf0 = c(5000, 'mephisto', 'hell', 'Perfect Ruby');
    set(1000, 1); out.gem_mf1000 = c(5000, 'mephisto', 'hell', 'Perfect Ruby');
    set(0, 1);   out.charm_mf0 = c(5000, 'mephisto', 'hell', "Gheed's Fortune");
    set(1000, 1); out.charm_mf1000 = c(5000, 'mephisto', 'hell', "Gheed's Fortune");
    set(0, 1);   out.anni_mf0 = c(5000, 'mephisto', 'hell', 'Annihilus');
    set(1000, 1); out.anni_mf1000 = c(5000, 'mephisto', 'hell', 'Annihilus');
    // THE MIRROR BUG: these are uniques on weapon bases whose names contain "Rune"
    set(0, 1);   out.magewrath_mf0 = c(5000, 'mephisto', 'hell', 'Magewrath');
    set(1000, 1); out.magewrath_mf1000 = c(5000, 'mephisto', 'hell', 'Magewrath');
    set(0, 1);   out.plague_mf0 = c(5000, 'mephisto', 'hell', 'Plague Bearer');
    set(1000, 1); out.plague_mf1000 = c(5000, 'mephisto', 'hell', 'Plague Bearer');
    set(0, 1);   out.jbs_mf0 = c(5000, 'mephisto', 'hell', 'Jah/Ber/Sur rune');
    set(1000, 1); out.jbs_mf1000 = c(5000, 'mephisto', 'hell', 'Jah/Ber/Sur rune');
    // /players: moves every farm silospen moves (Countess and Duriel too), and never Pindleskin
    set(699, 1); out.meph_p1 = c(5000, 'mephisto', 'hell', 'Frostburn');
    set(699, 8); out.meph_p8 = c(5000, 'mephisto', 'hell', 'Frostburn');
    set(699, 1); out.countess_p1 = c(5000, 'countess', 'hell', 'Ist Rune');
    set(699, 8); out.countess_p8 = c(5000, 'countess', 'hell', 'Ist Rune');
    set(699, 1); out.duriel_p1 = c(5000, 'duriel', 'hell', 'Frostburn');
    set(699, 8); out.duriel_p8 = c(5000, 'duriel', 'hell', 'Frostburn');
    set(699, 1); out.pindle_p1 = c(5000, 'pindle', 'hell', 'Frostburn');
    set(699, 8); out.pindle_p8 = c(5000, 'pindle', 'hell', 'Frostburn');
    // MF-blind item still obeys /players
    set(699, 1); out.rune_p1 = c(5000, 'mephisto', 'hell', 'Ist Rune');
    set(699, 8); out.rune_p8 = c(5000, 'mephisto', 'hell', 'Ist Rune');
    return out;
  });
  console.log('PROBE ' + JSON.stringify(probe, null, 1));

  expect(probe.uni_mf1000, 'MF must improve a unique (lower 1:N)').toBeLessThan(probe.uni_mf0);
  expect(probe.rune_mf1000, 'MF must NOT touch runes').toBe(probe.rune_mf0);
  expect(probe.gem_mf1000, 'MF must NOT touch gems').toBe(probe.gem_mf0);
  expect(probe.charm_mf1000, "MF must NOT touch Gheed's Fortune — it is a charm").toBe(probe.charm_mf0);
  expect(probe.anni_mf1000, 'MF must NOT touch Annihilus — it is a charm').toBe(probe.anni_mf0);
  expect(probe.jbs_mf1000, 'MF must NOT touch a High Rune row').toBe(probe.jbs_mf0);
  expect(probe.magewrath_mf1000, 'Magewrath is a UNIQUE on a Rune Bow — MF must still apply').toBeLessThan(probe.magewrath_mf0);
  expect(probe.plague_mf1000, 'Plague Bearer is a UNIQUE on a Rune Sword — MF must still apply').toBeLessThan(probe.plague_mf0);
  expect(probe.meph_p8, '/players must improve Mephisto').toBeLessThan(probe.meph_p1);
  // REG-2953 — silospen RotW 3.0 moves Countess (×1.39) and Duriel (×1.37) at /p8; only Pindleskin's table stays put
  expect(probe.countess_p8, 'Countess moves with /players (silospen ×1.39 at /p8)').toBeLessThan(probe.countess_p1);
  expect(probe.duriel_p8, 'Duriel moves with /players (silospen ×1.37 at /p8)').toBeLessThan(probe.duriel_p1);
  expect(probe.pindle_p8, 'Pindleskin is P#-proof — silospen does not move his table').toBe(probe.pindle_p1);
  expect(probe.rune_p8, 'a rune is MF-blind but still obeys /players').toBeLessThan(probe.rune_p1);
});
