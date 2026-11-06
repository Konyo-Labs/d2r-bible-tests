import { test, expect } from './_net_stub'; // diablo2.io art stubbed — kills net-flake (audit 2026-06-12)
import * as path from 'path';

const BIBLE = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v139 — platform-wide floating hover-image rollout. The same enlarged #arttip cursor
// popup the auras/items use now also fires for:
//   - super-unique bosses in the Bind-Demon table (.su-link) — explicitly Hephasto +
//     Lister — floating the verified diablo2.io SU monster avatar + name.
//   - runes — every .rune-stash-cell and runeword-recipe .mw-rune-chip floats the rune's
//     verified D2IO_ART icon.
// Additive: existing openBindSUByName / mwOpen / stash routing is untouched; only names
// that resolve in D2IO_ART get tagged (art-less SU stay a silent no-op, no broken image).

// SU that now carry a verified avatar (resolve in D2IO_ART)
// Desktop golden-merge added councilmember_graphic.png art for all 6 council members
// + Bartuc the Bloody — they are no longer art-less.
const SU_WITH_ART = [
  'Hephasto the Armorer', 'Lister the Tormentor', 'The Smith', 'Shenk the Overseer',
  'Bishibosh', 'Coldcrow', 'Rakanishu', 'Witch Doctor Endugu', 'Pitspawn Fouldog',
  'Battlemaid Sarina', 'Infector of Souls', 'Sharptooth Slayer',
  'Colenzo the Annihilator', 'Ventar the Unholy',
  'Ismail Vilehand', 'Geleb Flamefinger', 'Toorc Icefist', 'Bremm Sparkfist',
  'Wyand Voidbringer', 'Maffer Dragonhand', 'Bartuc the Bloody', 'Dac Farren',
];
// SU with NO verified avatar — must NOT get a data-arttip (no broken-image hover).
// v3876 (REG-3315): Dac Farren, the last one, got its in-game sprite (art/d2mon_Dac_Farren.gif), so
// the named list is empty. The law below no longer leans on a name: across EVERY bind .su-link, a
// link carries data-arttip exactly when artUrl answers for it - an art-less SU added later stays
// untagged, and an SU with art is never left bare.
const SU_NO_ART: string[] = [];
const ALL_RUNES = ['El','Eld','Tir','Nef','Eth','Ith','Tal','Ral','Ort','Thul','Amn','Sol',
  'Shael','Dol','Hel','Io','Lum','Ko','Fal','Lem','Pul','Um','Mal','Ist','Gul','Vex','Ohm',
  'Lo','Sur','Ber','Jah','Cham','Zod'];

test.describe('v139 super-unique + rune hover popups', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BIBLE);
    await page.waitForTimeout(800);
  });

  test('hovering the Hephasto bind link floats its verified SU avatar + name', async ({ page }) => {
    const r = await page.evaluate(() => {
      const el = document.querySelector('.su-link[data-arttip="Hephasto the Armorer"]') as HTMLElement | null;
      if (!el) return { found: false };
      const tip = document.getElementById('arttip')!;
      const img = tip.querySelector('img') as HTMLImageElement;
      el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, clientX: 300, clientY: 300 }));
      return {
        found: true,
        on: tip.classList.contains('on'),
        rich: tip.classList.contains('tip-rich'),
        name: tip.querySelector('.att-name')!.textContent,
        src: img.src,
        expected: (window as any).artUrl('Hephasto the Armorer'),
        imgShown: img.style.display !== 'none',
        clickThrough: getComputedStyle(tip).pointerEvents === 'none',
      };
    });
    expect(r.found).toBe(true);
    expect(r.on).toBe(true);
    expect(r.rich).toBe(false);          // image-only popup, not a rich stat card
    expect(r.name).toBe('Hephasto the Armorer');
    expect(r.src).toContain(r.expected);
    expect(r.imgShown).toBe(true);
    expect(r.clickThrough).toBe(true);
  });

  test('every verified-avatar SU is tagged + floats its mapped icon; art-less SU stay untagged', async ({ page }) => {
    const r = await page.evaluate(({ withArt, noArt }) => {
      const tip = document.getElementById('arttip')!;
      const img = tip.querySelector('img') as HTMLImageElement;
      const tagged: Record<string, { src: string; expected: string }> = {};
      for (const n of withArt) {
        const el = document.querySelector('.su-link[data-arttip="' + n + '"]') as HTMLElement | null;
        if (!el) { tagged[n] = { src: 'MISSING', expected: '' }; continue; }
        el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, clientX: 200, clientY: 200 }));
        tagged[n] = { src: img.src, expected: (window as any).artUrl(n) };
      }
      // art-less SU: the .su-link exists but must carry NO data-arttip
      const untagged: Record<string, boolean> = {};
      for (const n of noArt) {
        const links = Array.from(document.querySelectorAll('.su-link')) as HTMLElement[];
        const el = links.find((l) => (l.getAttribute('onclick') || '').includes("openBindSUByName('" + n + "'"));
        untagged[n] = !!el && !el.hasAttribute('data-arttip');
      }
      // the class law: every bind link is tagged exactly when its art resolves (REG-3315)
      const mismatch: string[] = [];
      let bindLinks = 0;
      for (const l of Array.from(document.querySelectorAll('.su-link')) as HTMLElement[]) {
        const m = (l.getAttribute('onclick') || '').match(/openBindSUByName\('([^']+)'/);
        if (!m) continue;
        bindLinks++;
        const has = !!(window as any).artUrl(m[1]);
        if (l.hasAttribute('data-arttip') !== has) mismatch.push(m[1] + (has ? ' has art but is untagged' : ' is tagged with no art'));
      }
      return { tagged, untagged, mismatch, bindLinks };
    }, { withArt: SU_WITH_ART, noArt: SU_NO_ART });
    expect(r.bindLinks, 'PREMISE: the bind table rendered its SU links').toBeGreaterThanOrEqual(15);
    expect(r.mismatch).toEqual([]);
    for (const n of SU_WITH_ART) {
      expect(r.tagged[n].src, n).toContain(r.tagged[n].expected);
    }
    for (const n of SU_NO_ART) {
      expect(r.untagged[n], n).toBe(true);
    }
  });

  test('all 33 runes resolve in D2IO_ART (incl. Jah=runeJo)', async ({ page }) => {
    const r = await page.evaluate((runes) => {
      const out: Record<string, string | null> = {};
      for (const n of runes) out[n] = (window as any).artUrl(n);
      return out;
    }, ALL_RUNES);
    for (const n of ALL_RUNES) {
      expect(r[n], n).toBeTruthy();
    }
    expect(r['Jah']).toMatch(/hd_jah_rune|runeJo_icon/);  // v384 HD rune sprite
    expect(r['Shael']).toMatch(/hd_shael_rune|runeShae_icon/);  // v384 HD rune sprite
  });

  // v253: rune-stash cells now float the rune's DESCRIPTION CARD (rich, with the HD icon
  // + its weapon/armor/shield stats), matching the item-hover behavior — not a bare icon.
  test('rune stash cells carry data-arttip and float the rune description card on hover (v253)', async ({ page }) => {
    const r = await page.evaluate(() => {
      (window as any).renderRuneStash();
      const cell = document.querySelector('.rune-stash-cell[data-arttip="Ber"]') as HTMLElement | null;
      if (!cell) return { found: false };
      const tip = document.getElementById('arttip')!;
      const img = tip.querySelector('img') as HTMLImageElement;
      cell.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, clientX: 250, clientY: 250 }));
      return {
        found: true,
        on: tip.classList.contains('on'),
        rich: tip.classList.contains('tip-rich'),
        src: img.src,
        expected: (window as any).artUrl('Ber'),
        desc: (tip.querySelector('.att-desc') as HTMLElement).innerHTML,
        clickThrough: getComputedStyle(tip).pointerEvents === 'none',
        anyTagged: document.querySelectorAll('.rune-stash-cell[data-arttip]').length,
      };
    });
    expect(r.found).toBe(true);
    expect(r.on).toBe(true);
    expect(r.rich).toBe(true);
    expect(r.src).toContain(r.expected);   // the rich card still leads with the HD rune icon
    expect((r.desc || '').toLowerCase()).toContain('weapon');  // …followed by its stats
    expect(r.clickThrough).toBe(true);
    expect(r.anyTagged).toBe(33);
  });

  test('runeword-recipe rune chips carry data-arttip and float their icon', async ({ page }) => {
    const r = await page.evaluate(() => {
      (window as any).mwOpen('Enigma');
      const chip = document.querySelector('.mw-rune-chip[data-arttip="Jah"]') as HTMLElement | null;
      if (!chip) return { found: false };
      const tip = document.getElementById('arttip')!;
      const img = tip.querySelector('img') as HTMLImageElement;
      chip.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, clientX: 220, clientY: 220 }));
      return { found: true, on: tip.classList.contains('on'), src: img.src, expected: (window as any).artUrl('Jah') };
    });
    expect(r.found).toBe(true);
    expect(r.on).toBe(true);
    expect(r.src).toContain(r.expected);
  });

  test('hover rollout does NOT break the item rich-card path + no console errors', async ({ page }) => {
    const errs: string[] = [];
    page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
    const r = await page.evaluate(() => {
      const f = (window as any)._arttipResolve;
      const soj = f('The Stone of Jordan');
      // hover a SU + a rune to shake out runtime errors
      (window as any).renderRuneStash();
      document.querySelectorAll('.su-link[data-arttip],.rune-stash-cell[data-arttip]').forEach((el) => {
        el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, clientX: 200, clientY: 200 }));
        el.dispatchEvent(new MouseEvent('mouseout', { bubbles: true }));
      });
      return { rich: soj.rich, type: /att-type/.test(soj.desc) };
    });
    await page.waitForTimeout(100);
    expect(r.rich).toBe(true);
    expect(r.type).toBe(true);
    expect(errs).toEqual([]);
  });
});
