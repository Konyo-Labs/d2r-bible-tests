import { test, expect } from './_net_stub';
import * as fs from 'fs';
import * as path from 'path';

// v1529 — NAMING THE MACHINE.
//
// Konyo: "the sigil. NAME ME it says but i cant really name it.. lol when i click it it just says
// copied."
//
// Two faults, and the second was the worse one:
//   1. the invitation and the action were different gestures — the pill asked for a name and a click
//      copied an id; naming was on double-click, hinted only inside a tooltip.
//   2. it probably never worked AT ALL: the old path called window.prompt(), which pywebview's
//      WebKit backend does not reliably implement, so in the app window — the only place this
//      console runs — a double-click could silently do nothing.
//
// So the rules this spec holds: when the pill asks for a name, clicking it gives one; the field is
// real DOM, not a dialog; and a name that fails to save says so.

const ORIGIN = 'http://tvd.console.test';
const UI_HTML = fs.readFileSync(path.resolve(__dirname, '..', 'tv', 'control_ui.html'), 'utf8');

const status = (nickname = '') => ({
  online: true, now: Date.now(), ver: 'v1529',
  identity: { id: 'a1b2c3d4e5f6', computer: 'konyo-3.local', user: 'konyo', nickname },
});

async function open(page: any, nickname = '', onName?: (body: any) => any) {
  await page.route(ORIGIN + '/ui', (r: any) =>
    r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: UI_HTML }));
  await page.route((u: URL) => u.pathname.startsWith('/api/')
    && !['/api/status', '/api/identity_name'].includes(u.pathname), (r: any) => r.abort());
  await page.route((u: URL) => u.pathname === '/api/status', (r: any) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(status(nickname)) }));
  await page.route((u: URL) => u.pathname === '/api/identity_name', (r: any) => {
    const body = JSON.parse(r.request().postData() || '{}');
    const out = onName ? onName(body) : { identity: { ...status(body.name).identity } };
    return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(out) });
  });
  await page.goto(ORIGIN + '/ui', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(900);          // the sigil has its own poll
}

test.describe('v1529 — when the pill asks for a name, clicking it gives one', () => {
  test('an unnamed machine invites a name', async ({ page }) => {
    await open(page, '');
    expect(await page.textContent('#sg-name')).toBe('name me');
    expect(await page.getAttribute('#sigil', 'title')).toContain('Click to name this machine');
  });

  test('★ clicking the invitation OPENS the field — it does not copy', async ({ page }) => {
    await open(page, '');
    await page.click('#sigil');
    await page.waitForTimeout(200);
    expect(await page.isVisible('#sg-edit')).toBe(true);
    expect(await page.isHidden('#sigil'), 'the field takes the pill’s place — no header reflow').toBe(true);
    // the old behaviour, which is what he actually hit
    expect(await page.textContent('#sg-name')).not.toBe('COPIED');
  });

  test('★ the field is real DOM, not a dialog — it types and it focuses', async ({ page }) => {
    // window.prompt is not reliably implemented by pywebview's WebKit backend, which is why the
    // old double-click-to-name could do nothing at all in the app window
    let dialogs = 0;
    page.on('dialog', (d: any) => { dialogs++; d.dismiss(); });
    await open(page, '');
    await page.click('#sigil');
    await page.waitForTimeout(200);
    expect(await page.evaluate(() => document.activeElement?.id)).toBe('sg-edit');
    await page.keyboard.type('DeanDush');
    expect(await page.inputValue('#sg-edit')).toBe('DeanDush');
    expect(dialogs, 'no dialog may be involved in naming').toBe(0);
  });

  test('Enter saves the name and the pill wears it', async ({ page }) => {
    let sent: any = null;
    await open(page, '', (body) => { sent = body; return { identity: { ...status(body.name).identity } }; });
    await page.click('#sigil');
    await page.keyboard.type('DeanDush');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(400);
    expect(sent).toEqual({ name: 'DeanDush' });
    expect(await page.textContent('#sg-name')).toBe('DeanDush');
    expect(await page.isHidden('#sg-edit')).toBe(true);
  });

  test('Escape cancels without saving', async ({ page }) => {
    let called = false;
    await open(page, '', (b) => { called = true; return { identity: status(b.name).identity }; });
    await page.click('#sigil');
    await page.keyboard.type('oops');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    expect(called).toBe(false);
    expect(await page.isVisible('#sigil')).toBe(true);
    expect(await page.textContent('#sg-name')).toBe('name me');
  });

  test('★ clicking away CANCELS — it never saves half a typed word', async ({ page }) => {
    let called = false;
    await open(page, '', (b) => { called = true; return { identity: status(b.name).identity }; });
    await page.click('#sigil');
    await page.keyboard.type('Dean');
    await page.click('body', { position: { x: 400, y: 400 } });
    await page.waitForTimeout(300);
    expect(called, 'a blur must not commit a partial name').toBe(false);
  });

  test('a NAMED machine keeps copy on click, and renames on double-click', async ({ page }) => {
    await open(page, 'DeanDush');
    expect(await page.textContent('#sg-name')).toBe('DeanDush');
    // v3864 (REG-3178) - the pill says COPIED only when the clipboard TOOK it, and a headless runner's clipboard refuses.
    // So this case hands the page a clipboard that takes the copy; the refused half is held by
    // tv/test_no_clipboard_copy_goes_unanswered.py.
    await page.evaluate(() => {
      Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: () => Promise.resolve() } });
    });
    await page.click('#sigil');
    await page.waitForTimeout(150);
    expect(await page.textContent('#sg-name'), 'copy is still the click action once it has a name').toBe('COPIED');
    await page.waitForTimeout(900);
    await page.dblclick('#sigil');
    await page.waitForTimeout(200);
    expect(await page.isVisible('#sg-edit')).toBe(true);
    expect(await page.inputValue('#sg-edit'), 'renaming starts from the current name').toBe('DeanDush');
  });

  test('★ a name that does NOT save says so — silence is what sent him here', async ({ page }) => {
    await open(page, '', () => ({ ok: false }));          // no identity back
    await page.click('#sigil');
    await page.keyboard.type('Nope');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
    const toasts = await page.$$eval('.toast, #toasts *, [class*="toast"]',
      (n: any[]) => n.map((x) => x.textContent).join(' | '));
    expect(toasts).toMatch(/not saved|could not/i);
  });

  test('the tooltip describes what THIS pill does, not pills in general', async ({ page }) => {
    await open(page, '');
    expect(await page.getAttribute('#sigil', 'title')).not.toContain('DOUBLE-CLICK to name');
    await open(page, 'DeanDush');
    expect(await page.getAttribute('#sigil', 'title')).toContain('double-click to rename');
  });
});
