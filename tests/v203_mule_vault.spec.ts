// v203 — THE VAULT mule manager (Tools centerpiece). Roster of mule "lockers"
// (default = the 10-mule warehouse blueprint), taxonomy auto-assign over the
// ✓ Owned pool (ITEM_CODEX base/rarity/setName + ITEM_TIP b/t fallback),
// drag-and-drop + click-assign, manifests export, and a 🏦 location badge on
// the item detail card. Persists d2r_muleRoster/d2r_muleAssign (rides backup).
import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');
const OWNED = ['Harlequin Crest (Shako)', 'The Stone of Jordan', 'Vampire Gaze',
  'Annihilus', 'Stormshield', 'Raven Frost', 'Tal Rasha set (any piece)', 'Windforce'];

test.describe('v203 the vault', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.evaluate(() => { (window as any).uiConfirm = () => Promise.resolve(true); }).catch(() => {});
    await page.waitForTimeout(2200);
    await page.evaluate((names) => {
      localStorage.removeItem('d2r_muleRoster');
      localStorage.removeItem('d2r_muleAssign');
      /* ⚠ CLEAR BEFORE SEEDING. This only ADDED, which assumes `owned` starts empty — it does
         not. The v677/v681 boot floor puts seed names into the physical vault before any fixture
         runs, so the dock already holds items and `chips === OWNED.length - 1` counts them too.
         Measured: 13 chips in CI against the 7 expected, and 35 on a browser profile that had been
         driven around, which is the same defect with a louder number.
         `localStorage.removeItem('d2r_owned')` would NOT do it — `owned` is a closure Set that is
         already in memory by now, which is exactly why this fixture reaches it through eval. So
         clear THAT, and the count becomes the fixture's own. [[feedback-blind-fixture-green-gate]] */
      eval('owned').clear();
      names.forEach((n: string) => eval('owned').add(n));
      (window as any).switchTab('tools');
      (window as any).renderVault();
    }, OWNED);
  });

  test('default roster renders 10 lockers (v360: + SHARED STASH; v342: + MAGIC & RARE); owned items appear as dock chips', async ({ page }) => {
    const r = await page.evaluate(() => ({
      mules: document.querySelectorAll('.vault-mule').length,
      chips: document.querySelectorAll('.vault-dock .vault-chip').length,
      names: [...document.querySelectorAll('.vm-name')].map(e => e.textContent),
      // ⚠ CARRY THE CHIP NAMES. The count alone said "expected 7, received 6" and nothing else, so
      // the only way to learn WHICH item was missing was to guess — and a guess about a machine
      // this one cannot enter is worth nothing. The names make the next failure self-diagnosing.
      chipNames: [...document.querySelectorAll('.vault-dock .vault-chip')]
        .map((c) => (c.textContent || '').replace(/[◆✕]/g, '').trim()),
      /* v2265 — AND WHERE ELSE AN ITEM CAN LEGITIMATELY BE. The dock holds what is NOT yet filed;
         a filed item lives in its locker as a .vm-cell. Both are "the vault can show you this". */
      cellNames: [...document.querySelectorAll('.vm-cell')]
        .map((c) => (c.textContent || '').replace(/[◆✕]/g, '').trim()),
      /* REG-2207 — a KEEP-IN-INVENTORY charm (Annihilus / Hellfire Torch / Gheed's Fortune) is kept on
         MAIN and never filed to a mule, so since v3721 it is NOT a dock chip and has no locker cell — it
         is shown in the "Don't mule to your alt" keep advisory as a .vk-chip. That IS the vault showing it.
         Before v3721 it sat loose in the dock where "Delete unsorted" could remove it from owned (data loss),
         so counting the dock alone would now mis-read the FIX as an item gone missing. The premise expired
         again — assert the fear (never nowhere), not the arrangement. */
      keepNames: [...document.querySelectorAll('.vk-chip')]
        .map((c) => (c.textContent || '').replace(/[◆✕×]/g, '').replace(/\s*\d+\s*$/, '').trim()),
      /* Elad 2026-10-18 — a name the router already knows is homed on the organizer
         at read time. It is not a dock chip and assign is not written, so it is not
         a locker cell either. The organizer row is the vault showing it. */
      orgNames: [...document.querySelectorAll('#vault-organize .vault-org-row[data-name]')]
        .map((c) => c.getAttribute('data-name') || ''),
    }));
    // v230: runes/essences/shards/statues → shared stash (RUNES-HIGH + MATS removed, 10→8).
    // v342: + MAGIC & RARE (8→9). v360: + SHARED STASH locker for the never-muled items (9→10).
    // v405: + RUNEWORDS locker (all forged runewords, weapon or armor) (10→11).
    // REG-2895: + CHARMS, the dedicated charm mule his 2026-10-28 ruling names (11→12).
    expect(r.mules).toBe(12);
    expect(r.names).toContain('CHARMS');
    expect(r.names).toContain('RUNEWORDS');
    expect(r.names).toContain('SHARED STASH');
    expect(r.names).toContain('MAGIC & RARE');
    expect(r.names).not.toContain('RUNES-HIGH');
    expect(r.names).not.toContain('MATS');
    // v227: 'Tal Rasha set (any piece)' is a grail ODDS row, not a physical
    // item — aggregates keep their calc ✓ but never become vault chips
    /* ⚠ v2265 — THE DOCK IS NOT THE WHOLE VAULT, AND SINCE v1980 IT NEVER WAS.
       This asserted that every owned item except the aggregate becomes a DOCK CHIP. That held while
       nothing arrived pre-filed. v1980 ("the sweep now mules what it registers") made the boot seed
       file what it registers, so 12 names are already assigned to lockers before any fixture runs —
       and this fixture cannot undo that the way it undoes `owned`: `owned` is reachable by eval,
       while `assign` is a closure variable inside the vault IIFE (bible.html:33546), so
       `eval('assign')` throws ReferenceError and removing d2r_muleAssign only clears the store the
       already-loaded object was built from.

       MEASURED on a real page: 6 dock chips, and Vampire Gaze — one of the seeded twelve — sitting
       in a .vm-cell in UNI-ARMOR, exactly where tvVaultRegister put it (mode 'already', mule
       'uni-armor'). Nothing was lost. The product is right and the premise expired.

       So assert the fear instead of the arrangement: an item he physically owns must be somewhere
       the vault can SHOW him — the dock if unfiled, its locker if filed — and never nowhere. That
       is what "an item vanished" would break, and it cannot be moved by which lane filed it first. */
    const expected = OWNED.filter((n) => n !== 'Tal Rasha set (any piece)').sort();
    const anywhere = new Set([...r.chipNames, ...r.cellNames, ...r.keepNames, ...r.orgNames]);  // REG-2207 keep advisory; v3767 organizer row for a router-homed name
    const unreachable = expected.filter((n) => !anywhere.has(n));
    expect(unreachable,
      `owned but nowhere in the vault — not a dock chip and not in any locker: ${JSON.stringify(unreachable)}`)
      .toEqual([]);
    /* and the aggregate still never becomes a physical row anywhere (v227) */
    expect(anywhere.has('Tal Rasha set (any piece)'),
      'the grail ODDS aggregate became a physical vault row').toBe(false);
    expect(r.names).toContain('SETS-TAL-IK');
    expect(r.names).toContain('UNI-SMALL');
  });

  // v226 — the AI-misread eraser: dock chips carry an ✕ that removes the
  // ✓ owned mark itself (not just the assignment), persisted. Born from the
  // 2026-06-13 incident: a pre-v225 scan registered Ist rune / Jah-Ber-Sur
  // rune / Tal Rasha set off a no-tooltip shards screenshot.
  test('v226 dock chip ✕ un-owns the item, persists, and leaves other items alone', async ({ page }) => {
    const r = await page.evaluate(() => {
      /* Windforce is a name the router homes, so it is an organizer row and not a dock
         chip (Elad 2026-10-18). Vault L1: Lenymo (a throw-out) is a THROW OUT task, not a
         dock chip either. The ✕ lives on a homeless dock chip: Obedience read only off a
         Chronicle page (his §28 ruling - found once, not held) has no home, so it is the chip. */
      eval('owned').add('Lenymo');
      eval('owned').add('Obedience');
      window._ownedProvWrite('Obedience', { source: 'intake-read', by: 'law', holder: 'Chronicle', loc: 'chronicle', scene: 'chronicle', sessionId: 's1', frameId: 'f1', ts: Date.now() });
      (window as any).renderVault();
      const chips = () => [...document.querySelectorAll('#vault-dock .vault-chip')] as HTMLElement[];
      const throwChip = chips().some((c: any) => c.dataset.vaultItem === 'Lenymo');
      const chip = chips().find((c: any) => c.dataset.vaultItem === 'Obedience') as HTMLElement;
      const btn = chip?.querySelector('.vc-unown') as HTMLElement;
      btn?.click();
      return {
        throwChip,
        hadBtn: !!btn,
        stillOwned: eval('owned').has('Obedience'),
        otherKept: eval('owned').has('Stormshield') && eval('owned').has('Lenymo'),
        chipGone: !chips().some((c: any) => c.dataset.vaultItem === 'Obedience'),
        persisted: !JSON.parse(localStorage.getItem('d2r_owned') || '[]').includes('Obedience'),
      };
    });
    expect(r.throwChip).toBe(false);   // L1: a throw-out is a THROW OUT task, never a dock chip
    expect(r.hadBtn).toBe(true);
    expect(r.stillOwned).toBe(false);
    expect(r.otherKept).toBe(true);
    expect(r.chipGone).toBe(true);
    expect(r.persisted).toBe(true);
  });

  test('taxonomy: sets→set lockers, jewelry/charms→small, helms/shields→armor; shared-stash items never mule', async ({ page }) => {
    const r = await page.evaluate(() => {
      const sug = (n: string) => { const s = (window as any).vaultSuggest(n); return s ? s.id : null; };
      return {
        tal: sug('Tal Rasha set (any piece)'), soj: sug('The Stone of Jordan'),
        gaze: sug('Vampire Gaze'), storm: sug('Stormshield'),
        anni: sug('Annihilus'), wf: sug('Windforce'),
        // v230 shared-stash guard: these must never get a mule (returns null)
        rune: sug('Ber Rune'), essence: sug('Essence of Hatred'),
        shard: sug('Worldstone Shard (Deep)'), statue: sug("Madawc's Ire"),
      };
    });
    expect(r.tal).toBe('sets-major');
    // v364: high trade-value items ("worth keeping close") auto-route to the SHARED cross-account stash
    // instead of their slot mule. SoJ is 'high' value → shared.
    expect(r.soj).toBe('shared');
    expect(r.gaze).toBe('shared');      // REG-2242: merc gear (Vampire Gaze) goes to shared
    expect(r.storm).toBe('uni-armor');  // low value → its slot mule
    // v409: Annihilus (like Hellfire Torch / Gheed's Fortune) only works in the ACTIVE character's
    // inventory — never muled and not shared (a charm in shared stash does nothing). → __keep sentinel.
    expect(r.anni).toBe('shared');      // REG-2241: torches and anni stay in shared
    expect(r.wf).toBe('uni-weap');      // med value → its slot mule
    // shared-stash items are explicitly excluded from muling
    expect(r.rune).toBeNull();
    expect(r.essence).toBeNull();
    expect(r.shard).toBeNull();
    expect(r.statue).toBeNull();
  });

  // v227 — the vault holds EXACT set pieces, never fabricated aggregates
  // (Konyo: '"Tal Rasha any piece"?? needs the exact individual item within
  // the set, and size accordingly — can't be fabricated').
  test('v227 exact set pieces: in the dock with slot-true sizes + set-locker routing; aggregate stays out', async ({ page }) => {
    const r = await page.evaluate(() => {
      eval('owned').add("Tal Rasha's Guardianship");
      eval('owned').add("Trang-Oul's Girth");
      (window as any).renderVault();
      const chips = [...document.querySelectorAll('#vault-dock .vault-chip')].map((c: any) => c.dataset.vaultItem);
      const org = [...document.querySelectorAll('#vault-organize .vault-org-row[data-name]')].map((c) => c.getAttribute('data-name'));
      return {
        pieceVocab: (window as any).__setPieceNames().length,
        aggInDock: chips.includes('Tal Rasha set (any piece)'),
        /* Elad 2026-10-18 — a set piece the router homes is an organizer row, not a dock chip. */
        guardInDock: chips.includes("Tal Rasha's Guardianship"),
        girthInDock: chips.includes("Trang-Oul's Girth"),
        guardShown: org.includes("Tal Rasha's Guardianship"),
        girthShown: org.includes("Trang-Oul's Girth"),
        guardSize: eval('vaultSize')("Tal Rasha's Guardianship"),   // armor → 2×3
        girthSize: eval('vaultSize')("Trang-Oul's Girth"),          // belt → 2×2 row family
        crestSize: eval('vaultSize')("Tal Rasha's Horadric Crest"), // helm → 2×2
        adjSize: eval('vaultSize')("Tal Rasha's Adjudication"),     // amulet → 1×1
        guardSug: (window as any).vaultSuggest("Tal Rasha's Guardianship").id,
        girthSug: (window as any).vaultSuggest("Trang-Oul's Girth").id,
      };
    });
    expect(r.pieceVocab).toBeGreaterThanOrEqual(50);
    expect(r.aggInDock).toBe(false);
    expect(r.guardInDock, 'a homed set piece is not an unsorted dock chip').toBe(false);
    expect(r.girthInDock, 'a homed set piece is not an unsorted dock chip').toBe(false);
    expect(r.guardShown, "Tal Rasha's Guardianship is homed on the organizer").toBe(true);
    expect(r.girthShown, "Trang-Oul's Girth is homed on the organizer").toBe(true);
    expect(r.guardSize).toEqual([2, 3]);
    expect(r.crestSize).toEqual([2, 2]);
    expect(r.adjSize).toEqual([1, 1]);
    expect(r.guardSug).toBe('sets-major');
    expect(r.girthSug).toBe('sets-rest');
  });

  test('v227 AI intake registers the exact piece AND ✓s the set grail row (calc-only)', async ({ page }) => {
    await page.route('**/api/intake', (route) =>
      route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ items: ["Tal Rasha's Lidless Eye"], unrecognized: [], usage: { in: 700, out: 20, cached: 0 } }),
      })
    );
    await page.evaluate(() => localStorage.setItem('d2r_intakeUrl', 'https://intake.test/api/intake'));
    await page.evaluate(async (b64: string) => {
      const w = window as any;
      /* Elad 2026-10-18 — AUTO INTAKE defaults off, so this photo door does not
         run until the world turns it on. The assertion is the intake outcome. */
      if (w.LSR) w.LSR.setItem('d2r_vaultAutoIntake', 'on');
      else localStorage.setItem('d2r_vaultAutoIntake', 'on');
      const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      const f = new File([bytes], 'shot.jpg', { type: 'image/jpeg' });
      await w.vaultIntake([f]);
    }, '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q==');
    const r = await page.evaluate(() => ({
      // #76 (v3751): a set piece is keyed on its SLOTTED ledger form
      piece: eval('owned').has("Tal Rasha's Lidless Eye (orb)"),
      grailRow: eval('owned').has('Tal Rasha set (any piece)'),
      chips: [...document.querySelectorAll('#vault-dock .vault-chip, .vm-item-row')].map((c: any) => c.dataset?.vaultItem || c.textContent),
      assigned: JSON.parse(localStorage.getItem('d2r_muleAssign') || '{}')["Tal Rasha's Lidless Eye (orb)"],
    }));
    expect(r.piece).toBe(true);
    expect(r.grailRow).toBe(true);             // grail ✓ rides along
    expect(r.assigned).toBe('sets-major');     // auto-filed to SETS-TAL-IK
  });

  test('#246 auto-assign files WITNESSES only — the owned pool stays in the dock; a witnessed filing persists and survives reload', async ({ page }) => {
    /* #246 W0 — REVERSED BY HIS RULING. This asserted that pressing auto-assign empties the dock: every
       owned name filed to a mule. `owned` is ticked-or-found-ever, and that exact press filed 173 names in
       his vault, 160 with no witness. The sorter now files only names that carry a witness. */
    await page.evaluate(() => (window as any).vaultAutoAssign());
    const r0 = await page.evaluate(() => {
      try { (window as any).renderVault(); } catch (e) {}
      const fold = (s: string) => String(s || '').replace(/[‘’ʼ´`]/g, "'").trim();
      const held = [...eval('owned')].map(fold);
      const dock = ((window as any)._vaultDockNames() || []).map(fold);
      const org = [...document.querySelectorAll('#vault-organize .vault-org-row[data-name]')]
        .map((c) => fold((c as HTMLElement).getAttribute('data-name') || ''));
      const keep = [...document.querySelectorAll('.vk-chip')]
        .map((c) => fold((c.textContent || '').replace(/[◆✕×]/g, '').replace(/\s*\d+\s*$/, '')));
      return {
        owned: held, dock, org, keep,
        stored: JSON.parse(localStorage.getItem('d2r_muleAssign') || '{}'),
      };
    });
    /* Elad 2026-10-18 — the sorter still must not write assign for an unwitnessed
       name. The owned pool stays owned, and each name stays on a painted surface:
       the dock if it is homeless, the organizer row if the seam homed it. */
    const seeded = ['Harlequin Crest (Shako)', 'The Stone of Jordan', 'Vampire Gaze', 'Annihilus', 'Stormshield', 'Raven Frost', 'Windforce'];
    const painted = new Set([...r0.dock, ...r0.org, ...r0.keep]);
    const lost = seeded.filter((n) => !r0.owned.includes(n));
    const invisible = seeded.filter((n) => !painted.has(n));
    expect(lost, 'the owned pool lost a seeded name').toEqual([]);
    expect(invisible, 'a seeded name is owned but not on a painted surface (dock or seam home)').toEqual([]);
    const filed = seeded.filter((n) => r0.stored[n] != null);
    expect(filed, 'the sorter filed owned names that carry no witness').toEqual([]);
    expect(r0.stored['The Stone of Jordan'], 'an owned name was filed with no witness').toBeUndefined();
    // a WITNESSED item goes through the one door; the router still decides its mule
    await page.evaluate(() => (window as any).vaultFile('The Stone of Jordan', { lane: 'stash', sessions: [
      { session: 's_a', frame: 'f_a.jpg', conf: 0.9 }, { session: 's_b', frame: 'f_b.jpg', conf: 0.85 }] }));
    const r1 = await page.evaluate(() => ({
      stored: JSON.parse(localStorage.getItem('d2r_muleAssign') || '{}'),
      prov: JSON.parse(localStorage.getItem('d2r_vaultProv') || '{}'),
    }));
    // v364: SoJ is high trade value → auto-routes to the SHARED cross-account stash, not uni-small.
    expect(r1.stored['The Stone of Jordan']).toBe('shared');
    expect(r1.prov['The Stone of Jordan'] && r1.prov['The Stone of Jordan'].source, 'the filing left no witness row').toBe('stash');
    // persist owned BEFORE reloading — the vault prunes assignments of
    // un-owned items at load (eval('owned').add bypasses persistence)
    await pinEvaluate(page, () => localStorage.setItem('d2r_owned', JSON.stringify([...eval('owned')])));
    await reloadPinned(page);
    await page.evaluate(() => { (window as any).uiConfirm = () => Promise.resolve(true); }).catch(() => {});
    await page.waitForTimeout(2200);
    const r2 = await page.evaluate(() => {
      (window as any).renderVault();
      const shared = document.querySelector('[data-vault-mule="shared"]')!;
      return { sharedCount: shared.querySelector('.vm-count')!.textContent, stored: JSON.parse(localStorage.getItem('d2r_muleAssign') || '{}')['The Stone of Jordan'] };
    });
    expect(r2.stored).toBe('shared');                  // assignment persisted across reload
    expect(Number(r2.sharedCount)).toBeGreaterThanOrEqual(1); // SoJ in the SHARED locker
  });

  test('click-assign (chip → locker) and unassign round-trip', async ({ page }) => {
    await page.evaluate(() => {
      /* Windforce is seam-homed, so it is not a dock chip. Vault L1: a throw-out (Lenymo) is a
         THROW OUT task, not a chip. A Chronicle-only Obedience has no home, so it is the dock
         chip. The click-assign law is the chip, not which item it is. */
      eval('owned').add('Obedience');
      window._ownedProvWrite('Obedience', { source: 'intake-read', by: 'law', holder: 'Chronicle', loc: 'chronicle', scene: 'chronicle', sessionId: 's1', frameId: 'f1', ts: Date.now() });
      (window as any).renderVault();
      const chip = [...document.querySelectorAll('#vault-dock .vault-chip')].find(c => (c as HTMLElement).dataset.vaultItem === 'Obedience') as HTMLElement;
      chip.click();
    });
    await page.evaluate(() => {
      (document.querySelector('[data-vault-mule="wip"] .vm-plate') as HTMLElement).click();
    });
    const r = await page.evaluate(() => JSON.parse(localStorage.getItem('d2r_muleAssign') || '{}'));
    expect(r['Obedience']).toBe('wip');
    await page.evaluate(() => (window as any).vaultUnassign('Obedience'));
    const r2 = await page.evaluate(() => JSON.parse(localStorage.getItem('d2r_muleAssign') || '{}'));
    expect(r2['Obedience']).toBeUndefined();
  });

  test('the 🏦 location badge renders on the item detail card and jumps to the vault', async ({ page }) => {
    await page.evaluate(() => {
      (window as any).vaultAssign('Harlequin Crest (Shako)', 'uni-armor');
      (window as any).openItemDetail('Harlequin Crest (Shako)');
    });
    const badge = await page.evaluate(() => document.querySelector('#item-detail-panel .vault-loc-badge')?.textContent || '');
    expect(badge).toContain('UNI-ARMOR');
    await page.evaluate(() => (document.querySelector('#item-detail-panel .vault-loc-badge') as HTMLElement).click());
    await page.waitForTimeout(500);
    const tab = await page.evaluate(() => (document.querySelector('.tabs .tab.active') as HTMLElement)?.dataset.tab);
    // v2084 gave the Vault Manager a main tab of its own and v2090 forwarded every old address to
    // it: window.vaultJump — the handler this badge fires (bible.html:35377) — now calls
    // switchTab('vault') (bible.html:35382), not switchTab('tools'). The law is unchanged, the
    // room moved: the badge must land him where the card actually is.
    expect(tab).toBe('vault');
  });

  // Vault v3 (Elad 14:32 IDT 2026-10-24): Copy manifests (window.vaultExport) was removed whole - the approved removal;
  // its absence is proved in tv/test_vault_v3_layout_keeps_every_door.py. The mule round-trip below is unchanged.
  test('add/rename/delete mule round-trip', async ({ page }) => {
    const r = await page.evaluate(async () => {
      (window as any).vaultAutoAssign();
      (window as any).prompt = () => 'TEST-MULE';
      (window as any).vaultAddMule();
      const added = [...document.querySelectorAll('.vm-name')].some(e => e.textContent === 'TEST-MULE');
      (window as any).confirm = () => true;
      const id = JSON.parse(localStorage.getItem('d2r_muleRoster')!).find((m: any) => m.name === 'TEST-MULE').id;
      await (window as any).vaultDeleteMule(id);   // v341.60 — async (awaits uiConfirm); await before checking it's gone
      const gone = ![...document.querySelectorAll('.vm-name')].some(e => e.textContent === 'TEST-MULE');
      return { added, gone, exportGone: typeof (window as any).vaultExport === 'undefined' };
    });
    expect(r.added).toBe(true);
    expect(r.gone).toBe(true);
    expect(r.exportGone).toBe(true);
  });

  test('no console errors through the full vault flow', async ({ page }) => {
    const errs: string[] = [];
    page.on('pageerror', e => errs.push(e.message));
    await page.evaluate(() => {
      (window as any).vaultAutoAssign();
      (window as any).renderVault();
      (window as any).openItemDetail('Stormshield');
    });
    await page.waitForTimeout(500);
    expect(errs).toEqual([]);
  });
});
