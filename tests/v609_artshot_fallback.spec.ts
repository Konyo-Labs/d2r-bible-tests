import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v609 — Konyo: "no shot where it should be HD photos of that specific item". A card whose read has
// no stored screenshot now shows THAT ITEM's own in-game HD sprite in the shot slot (clickable →
// its card) instead of a dead "no shot" box — in BOTH the Socketed & Larzuk Review and the
// Throw-Out Review. "no shot" only remains when the item has no resolvable art at all.

test('shot slot falls back to the item\'s own HD art in both review sections', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    const w: any = window;
    // a registered socketed base with NO journal shot → Socketed Review card
    w._ensureSocketBaseEntry && w._ensureSocketBaseEntry('Bone Visage (3os)', true);
    const own = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
    if (own.indexOf('Bone Visage (3os)') < 0) own.push('Bone Visage (3os)');
    localStorage.setItem('d2r_owned', JSON.stringify(own));
    // a throw-out read with NO shot → Throw-Out Review card
    localStorage.setItem('d2r_unknownReads', JSON.stringify(['Grim Scythe (4os low base)']));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    w.switchTab && w.switchTab('tools');
    w.renderVault && w.renderVault();
    const probe = (rootId: string, name: string) => {
      const root = document.getElementById(rootId);
      const card = root && Array.from(root.querySelectorAll('.to-card')).find((c) => (c.textContent || '').includes(name));
      if (!card) return { found: false };
      const art = card.querySelector('.to-shot.to-artshot img') as HTMLImageElement | null;
      return { found: true, hasArt: !!art, src: art ? (art.getAttribute('src') || '').slice(0, 60) : '',
               saysNoShot: /no shot/.test(card.textContent || '') };
    };
    const out = { sock: probe('vault-socketed', 'Bone Visage'), thr: probe('vault-throwout', 'Grim Scythe') };
    localStorage.removeItem('d2r_owned'); localStorage.removeItem('d2r_unknownReads');
    return out;
  });
  expect(r.sock.found).toBe(true);
  expect(r.sock.hasArt).toBe(true);          // Bone Visage's OWN sprite fills the slot…
  expect(r.sock.saysNoShot).toBe(false);     // …and the dead "no shot" box is gone
  expect(r.thr.found).toBe(true);
  expect(r.thr.hasArt).toBe(true);           // same in the Throw-Out Review (Grim Scythe's sprite)
  expect(r.thr.saysNoShot).toBe(false);
});

// v609.1 — the TAGGED-to-folder chain: a card whose read has a stored FILENAME must never degrade to
// a dead box. Permission lapsed (browser restart) → "📂 tap to load" re-authorize; folder/file truly
// gone → the item's own HD art, click-to-enlarge. (Stub the folder fns — headless has no real handle.)
test('tagged placeholder: prompt → tap-to-load; gone → HD art fallback', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(async () => {
    const w: any = window;
    const mk = () => {
      const wrap = document.createElement('div');
      wrap.innerHTML = '<div class="to-shot to-noshot" data-ffsrc="Screenshot X.png" data-artfb="art/hd_bone_visage.png">📂 …</div>';
      document.body.appendChild(wrap);
      return wrap;
    };
    w._vShotFromFolder = async () => null;               // hydration always fails in headless
    // case 1: permission lapsed → tap-to-load
    w._vFolderPerm = async () => 'prompt';
    const a = mk(); w._vHydrateShots(a);
    await new Promise((res) => setTimeout(res, 300));
    const tap = (a.textContent || '').includes('tap to load');
    // case 2: folder gone → art fallback with the ITEM's art, click-to-enlarge
    w._vFolderPerm = async () => 'none';
    const b = mk(); w._vHydrateShots(b);
    await new Promise((res) => setTimeout(res, 300));
    const art = b.querySelector('.to-artshot img') as HTMLImageElement | null;
    a.remove(); b.remove();
    return { tap, artSrc: art ? art.getAttribute('src') : null, deadBox: /no shot/.test(b.textContent || '') };
  });
  expect(r.tap).toBe(true);                              // restart → one-tap re-authorize, not "no shot"
  /* v1681 — SPLIT THE PATH FROM THE CACHE-BUSTER. This asserted exact string equality against
     'art/hd_bone_visage.png' and had been failing on CI shard 6 since v1643 gave every art seam an
     `_artV()` stamp — the src is now 'art/hd_bone_visage.png?v=v1680', so the assertion went red on
     every version bump, forever, for a reason that has nothing to do with the fallback.
     The product is RIGHT and the spec described an older shape. So it now checks the two things
     that actually matter, separately: the resolved PATH is that item's own art, and the stamp is
     PRESENT — because v1643 exists so a repaired art file is not left invisible behind a cached
     copy, and silently accepting an unstamped src would let that regress unnoticed. */
  expect(r.artSrc?.split('?')[0]).toBe('art/hd_bone_visage.png');   // truly gone → THAT item's art
  expect(r.artSrc, 'the art fallback lost its v1643 cache-bust stamp').toMatch(/\?v=/);
  expect(r.deadBox).toBe(false);
});
