import { test, expect } from './_net_stub'; // diablo2.io art stubbed — kills net-flake (audit 2026-06-12)
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v78 — the 9 Uber Boss ID cards in the Ancients/Pinnacle tab. Three mini-ubers
// (Lilith → Diablo's Horn, Uber Izual → Mephisto's Brain, Uber Duriel → Baal's
// Eye), the three Uber Tristram trio (Uber Mephisto / Uber Diablo / Uber Baal →
// Hellfire Torch), and the three Colossal Ancients (Talic / Korlic / Madawc →
// Colossal Jewels). Each card is expandable, carries verified monster stats
// (diablo2.io / Arreat Summit), routes its drop to the material card via openDrop,
// and is resolvable from the global search via jumpToUberBoss.
test.describe('v78 Uber Boss ID cards (9)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.waitForTimeout(1200);
  });

  test('UBER_BOSSES exposes all 9 bosses across the 3 groups', async ({ page }) => {
    const data = await page.evaluate(() => (window as any).UBER_BOSSES);
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBe(9);
    const ids = data.map((b: any) => b.id);
    expect(ids).toEqual([
      'lilith', 'izual', 'uber-duriel',
      'uber-mephisto', 'uber-diablo', 'uber-baal',
      'talic', 'korlic', 'madawc',
    ]);
    // verified drop mapping for the 3 mini-ubers
    const byId = Object.fromEntries(data.map((b: any) => [b.id, b]));
    expect(byId['lilith'].drop).toBe("Diablo's Horn");
    expect(byId['izual'].drop).toBe("Mephisto's Brain");
    expect(byId['uber-duriel'].drop).toBe("Baal's Eye");
    // the trio have no organ drop (torch via Standard of Heroes)
    expect(byId['uber-mephisto'].drop).toBe(null);
    expect(byId['uber-diablo'].drop).toBe(null);
    expect(byId['uber-baal'].drop).toBe(null);
    // Colossal Ancients drop the jewels
    expect(byId['talic'].drop).toBe('Colossal Ancient Jewels');
  });

  test('renderUberBossCards renders 9 collapsible cards with portraits', async ({ page }) => {
    const r = await page.evaluate(() => {
      const box = document.getElementById('uber-boss-cards')!;
      const cards = [...box.querySelectorAll('.uber-boss-card')];
      const imgs = cards.map((c) => (c.querySelector('.d2art-img') as HTMLImageElement)?.getAttribute('src') || '');
      return {
        fn: typeof (window as any).renderUberBossCards,
        count: cards.length,
        // Desktop golden-merge: Colossal Ancients (Talic/Korlic/Madawc) art resolved
        // from D2IO_ART as avatar gallery .gif URLs, not /items/ .png — accept both.
        allHaveArt: imgs.every((s) => /^art\//.test(s) && /\.(png|gif)(?:\?|$)/.test(s)),
        allHidden: cards.every((c) => c.querySelector('.ubc-body')!.hasAttribute('hidden')),
        lilithArt: imgs[0],
        baalArt: imgs[5],
      };
    });
    expect(r.fn).toBe('function');
    expect(r.count).toBe(9);
    expect(r.allHaveArt).toBe(true);
    expect(r.allHidden).toBe(true);               // collapsed by default
    // REG-3321 (v3877 #102/#91): one ANIMATED sprite per monster, never a stone-backed render. REG-3357 (v3879 #108/#109,
    // his ask "ubers differ"): an uber wears ITS OWN sprite, apart from its regular boss - Lilith is not Andariel's picture.
    expect(r.lilithArt).toMatch(/d2mon_Lilith\.gif(?:\?|$)/);
    expect(r.baalArt).toMatch(/d2arreat_baal\.gif(?:\?|$)/);
    expect(r.lilithArt).not.toMatch(/d2mon_Andariel\.gif/);   // the uber is not drawn as its regular boss
    expect(r.baalArt).not.toMatch(/d2mon_Baal\.gif/);
  });

  // REG-2504..2506 (#68): Uber Duriel's Hell resists are physical 50 and 75 for the rest (d2emu) - no resist reaches
  // 100, so the card says immune 'none' and the 75s, never "Cold immune" beside a cold resist of 75.
  test('verified immunities show in the stat block (Mephisto Lit+Pois, Uber Duriel none - 75 resists)', async ({ page }) => {
    const r = await page.evaluate(() => {
      (window as any).toggleUberBoss('uber-mephisto');
      (window as any).toggleUberBoss('uber-duriel');
      const meph = document.getElementById('uberboss-uber-mephisto')!;
      const dur = document.getElementById('uberboss-uber-duriel')!;
      return {
        mephOpen: !meph.querySelector('.ubc-body')!.hasAttribute('hidden'),
        mephImmune: meph.querySelector('.ubc-immune strong')!.textContent,
        mephBody: meph.textContent || '',
        durImmune: dur.querySelector('.ubc-immune strong')!.textContent,
        durBody: dur.textContent || '',
        durMlvl: dur.querySelector('.ubc-stat strong')!.textContent,
      };
    });
    expect(r.mephOpen).toBe(true);
    expect(r.mephImmune).toMatch(/Lightning \+ Poison/);
    expect(r.mephBody).toMatch(/Conviction aura/);
    expect(r.durImmune).toBe('none');
    expect(r.durBody).toMatch(/Magic\/Fire\/Cold\/Light\/Poison 75/);
    expect(r.durBody).not.toMatch(/Cold immune/);
    expect(r.durMlvl).toBe('110');
  });

  test('mini-uber drop routes to its organ material card; trio routes to Torch', async ({ page }) => {
    // Lilith → Diablo's Horn
    const horn = await page.evaluate(() => {
      (window as any).toggleUberBoss('lilith');
      const card = document.getElementById('uberboss-lilith')!;
      (card.querySelector('.ubc-drop .zd-item-click') as HTMLElement).click();
      const d = document.querySelector('#item-detail .material-card');
      return { has: !!d, text: d?.textContent || '' };
    });
    expect(horn.has).toBe(true);
    expect(horn.text).toMatch(/Diablo's Horn/);
    // Uber Baal → Hellfire Torch
    const torch = await page.evaluate(() => {
      (window as any).toggleUberBoss('uber-baal');
      const card = document.getElementById('uberboss-uber-baal')!;
      (card.querySelector('.ubc-drop .zd-item-click') as HTMLElement).click();
      const d = document.querySelector('#item-detail .material-card');
      return { has: !!d, text: d?.textContent || '' };
    });
    expect(torch.has).toBe(true);
    expect(torch.text).toMatch(/Hellfire Torch/);
  });

  test('toggleUberBoss expands and collapses a card', async ({ page }) => {
    const r = await page.evaluate(() => {
      const card = document.getElementById('uberboss-talic')!;
      const body = card.querySelector('.ubc-body')!;
      const before = body.hasAttribute('hidden');
      (window as any).toggleUberBoss('talic');
      const open = !body.hasAttribute('hidden') && card.classList.contains('open');
      (window as any).toggleUberBoss('talic');
      const closed = body.hasAttribute('hidden') && !card.classList.contains('open');
      return { before, open, closed };
    });
    expect(r.before).toBe(true);
    expect(r.open).toBe(true);
    expect(r.closed).toBe(true);
  });

  test('global search resolves "korlic" and routes via jumpToUberBoss', async ({ page }) => {
    await page.fill('#gsearch-input', 'korlic');
    await page.waitForTimeout(220);
    const labs = await page.evaluate(() => [...document.querySelectorAll('#gsearch-results .gsearch-item')]
      .map((el) => (el.querySelector('.gsearch-lab') as HTMLElement)?.textContent?.trim() || ''));
    expect(labs.some((l) => /Korlic/.test(l))).toBe(true);
    // routing function exists + opens the card in the ancients tab
    const routed = await page.evaluate(async () => {
      (window as any).jumpToUberBoss('korlic');
      await new Promise((res) => setTimeout(res, 220));
      const card = document.getElementById('uberboss-korlic')!;
      return !card.querySelector('.ubc-body')!.hasAttribute('hidden');
    });
    expect(routed).toBe(true);
  });

  test('Pandemonium Diablo is distinguished from the SoJ Diablo Clone', async ({ page }) => {
    const txt = await page.evaluate(() => {
      (window as any).toggleUberBoss('uber-diablo');
      return document.getElementById('uberboss-uber-diablo')!.textContent || '';
    });
    expect(txt).toMatch(/Pandemonium Diablo/);
    expect(txt).toMatch(/Immune Fire \+ Cold/);
    expect(txt).toMatch(/Pit Lords/);
    expect(txt).toMatch(/Clone/); // explicitly disambiguated
  });

  test('no console errors across the uber-boss-card flow', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
    await page.goto(URL);
    await page.waitForTimeout(1200);
    await page.evaluate(() => {
      (window as any).renderUberBossCards();
      ['lilith', 'izual', 'uber-mephisto', 'madawc'].forEach((id) => {
        try { (window as any).toggleUberBoss(id); } catch (e) {}
      });
      (window as any).jumpToUberBoss('uber-baal');
    });
    await page.waitForTimeout(200);
    expect(errors).toEqual([]);
  });
});
