/**
 * /api/console — console-app presence beacon (v875, fleet-scan rebuilt v1596).
 *
 * SCOPE — read this before believing what this surface says. It tracks the TV DIABLO
 * console APP checking in from a machine. It does NOT track browser page-views of
 * /d2r/ — those are a separate tracker at /visits (functions/visits.js, fed by
 * recordVisit() in functions/_middleware.js). A machine that only ever opened the
 * bible in a browser will NEVER appear here, by design, and that is not a bug.
 *
 * The control app (Mac + Windows + cousins) POSTs here on boot, on ON AIR / OFF
 * transitions, and every ~4 min as a heartbeat. Storage reuses the TZ_HISTORY KV:
 *   console:<machine>         — CURRENT state, rewritten on a material change or every REFRESH_S (15 min),
 *                               TTL PRESENCE_TTL (40 min) → key alive ⇔ console online (REG-3023: this
 *                               line said "TTL 10 min" for a key that lives 40)
 *   consolelog:<ts>:<machine> — event log entries (boot/onair/off only, no heartbeats), TTL 30d
 *   lastseen:<machine>        — DURABLE last check-in, TTL 400d, written on EVERY beacon
 *                               INCLUDING heartbeats. One key per machine, so it can never
 *                               fall out of a scan window the way a growing event log can.
 *                               'lastseen:' collides with no other prefix in use here
 *                               ('console:', 'consolelog:', 'visit:').
 *
 * WHY lastseen: EXISTS (the bug it retires) — the offline list used to be reconstructed
 * from `kv.list({ prefix: 'consolelog:', limit: 400 })`. Cloudflare KV returns keys "in
 * lexicographically sorted order according to their UTF-8 bytes" (developers.cloudflare.com
 * /kv/api/list-keys/, verified 2026-08-02), the keys are 'consolelog:<ISO-ts>:<machine>',
 * so ascending == OLDEST FIRST. limit:400 therefore returned the OLDEST 400 events in the
 * 30-day window and never the newest: once the log passed 400 entries every RECENT machine
 * fell outside it and went invisible. Konyo's exact symptom — his cousin ran the console
 * yesterday and did not appear, live GET answered online=[konyo-3], offline=[].
 * Fixed by paginating the FULL cursor (correct under ascending AND descending ordering,
 * which is the point) and by making lastseen: the primary source.
 *
 * REFUTED, DO NOT RE-OPEN — there is no 'console:' / 'consolelog:' prefix collision.
 * `'consolelog:2026-08-01T00:00:00Z:x'.startsWith('console:')` is FALSE (byte 8 is ':'
 * in one and 'l' in the other), so the presence list() below cannot match event-log keys.
 * Investigated and executed 2026-08-02; pinned by a test in tv/test_console_fleet.py.
 * No defensive filter is added for it on purpose: dead code that can never fire reads to
 * the next maintainer as evidence the bug was real.
 *
 * Auth: sits behind the site-wide Basic gate (_middleware) like every /api route.
 * View at /console?k=<VISITS_KEY> — Konyo-only, same key as /visits.
 */

// v3387 — ONE normaliser for both ends of the presence join. The writer lives in
// functions/_middleware.js; importing it is deliberate, because two copies of a normaliser is
// exactly how the two console files already shared one bug (see the listAll note below).
import { webSeenSlug } from '../_middleware.js';

/**
 * List EVERY key under a prefix by following the cursor. KV caps a single list() at 1000
 * keys and signals more via list_complete/cursor; an empty keys array does NOT mean done
 * (expired keys are iterated but not returned), so the loop trusts list_complete only.
 *
 * KEEP THIS BLOCK BYTE-IDENTICAL to the copy in functions/console.js — the two files
 * already shared the oldest-first bug once because they were copy-pasted, and the way to
 * stop that recurring is for the shared part to be obviously, diffably the same.
 */
async function listAll(kv, prefix) {
  const keys = []; let cursor;
  for (let i = 0; i < 50; i++) {                    // hard cap 50 pages x 1000 = 50k keys
    const page = await kv.list({ prefix, limit: 1000, cursor });
    keys.push(...page.keys);
    if (page.list_complete || !page.cursor) break;
    cursor = page.cursor;
  }
  return keys;
}

const PAGE_CAP = 50, PAGE_SIZE = 1000;              // must match listAll's loop bound / limit

/**
 * v1597.1 — READ THE KEY, NOT THE VALUE. This is a HARD Cloudflare limit, not a nicety.
 *
 * Fixing the oldest-400 window meant listing every `consolelog:` key — 2,556 of them on the real
 * store — and the first fix then did one kv.get() per key to learn which machine each event was
 * from. That is 2,556 subrequests in one invocation, and Workers cap subrequests per invocation:
 * `/console` began returning HTTP 500 with "Too many API requests by single Worker invocation"
 * (captured from `wrangler pages deployment tail`, not guessed). The bug fix had a bug.
 *
 * The reads were never necessary. The key IS the record for this purpose:
 *     consolelog:<ISO-timestamp>:<machine>
 * so machine and time parse straight out of the name, at a cost of zero subrequests. Only the
 * machines actually SHOWN need their detail row fetched, and there are a handful of those.
 *
 * Split on the LAST ':' rather than a fixed index — an ISO timestamp contains colons, so
 * `parts[1]` is the hour, not the machine.
 *
 * KEEP BYTE-IDENTICAL with the copy in functions/console.js.
 */
function machinesFromLogKeys(keys) {
  const newest = new Map();                          // machine -> ISO timestamp of its latest event
  for (const k of keys) {
    const name = (k && k.name) || '';
    if (!name.startsWith('consolelog:')) continue;
    const rest = name.slice('consolelog:'.length);
    const cut = rest.lastIndexOf(':');
    if (cut <= 0) continue;
    const t = rest.slice(0, cut);
    const machine = rest.slice(cut + 1);
    if (!machine) continue;
    const prev = newest.get(machine);
    if (!prev || prev.t < t) newest.set(machine, { machine, t, key: name });
  }
  return [...newest.values()];
}

/* REG-1839 — A SENTENCE CUT WITH NO MARK READS AS A WHOLE ONE. Eight places here cut a console's own words at 160
   with a bare slice, so the fleet row read "...relaunch it WITH a window; and the board has not" and stopped, as if that
   were the reason; five more did the same at 120-200. ONE cut for all of them: at the last word that fits, and an
   ellipsis says something was left out. Text that fits comes back as it came. A single token longer than half the room
   keeps a hard cut rather than nothing. The console's twin is control_app._word_cut, and a law drives both over the
   same sentences. Top level, so every shaper below shares it; a law that lifts one shaper into node lifts this with it
   (tv/worker_source.py). */
function cutAtWord(v, n) {
  const s = String(v == null ? '' : v);
  if (s.length <= n) return s;
  let head = s.slice(0, Math.max(1, n - 1));
  if (/\S/.test(s.charAt(head.length))) {
    const word = head.replace(/\s+\S*$/, '');
    if (word.length >= n / 2) head = word;
  }
  const t = head.replace(/[\s,;:.\u2013\u2014-]+$/, '');
  return (t || head) + '\u2026';
}

export async function onRequestPost(context) {
  const { request, env } = context;
  const kv = env && env.TZ_HISTORY;
  if (!kv) return json({ ok: false, error: 'storage unavailable' }, 500);

  let body = {};
  try { body = await request.json(); } catch (e) { body = {}; }
  const machine = String(body.machine || 'unknown').slice(0, 40).replace(/[^\w.-]/g, '_');
  const event = String(body.event || 'hb').slice(0, 12);

  const cf = request.cf || {};
  const rec = {
    t: new Date().toISOString(),
    machine,
    platform: String(body.platform || '').slice(0, 12),
    ver: String(body.ver || '').slice(0, 12),
    mode: String(body.mode || '').slice(0, 12),
    event,
    user: String(body.user || '').slice(0, 24),
    // v1496 — the FRIENDLY name Konyo gave this machine in its console ("Konyo's MacBook").
    // The hostname stays as the technical fallback; a nickname is what he actually reads.
    nickname: String(body.nickname || '').slice(0, 40),
    install: String(body.install || '').slice(0, 12),
    reads: Number(body.reads || 0) || 0,
    // ══ v2257 — THE FOURTH, FIFTH AND SIXTH JOINT OF THE SAME DEFECT, and I made all three ══
    //
    // v2254 added `diskVer`, v2255 `relaunch`, v2256 `pull` — each posted faithfully by the
    // console, each dropped HERE, because `rec` is a fixed key list and none of them was on it.
    // Three versions of work that could not reach his screen no matter how correct the console
    // was, and the comment on `tally` directly below already describes this exact failure:
    // "built on both ends, never joined, and silent by construction."
    //
    // ⚠ THE TELL WAS ON HIS OWN ROW. His console reported `run v2256` — a build that sends all
    // three — beside `disk (none)` and `pull —`. A machine cannot be running code that emits a
    // field and be silent about it; that contradiction was the whole finding.
    // [[plumbing-with-no-tap]] [[the-unjoined-end]]
    //
    // Shaped here rather than trusted, the same standard the tally uses: strings are clamped,
    // booleans are booleans, and anything unrecognised becomes null so "we could not tell" can
    // never read as an answer.
    diskVer: String(body.diskVer || '').slice(0, 12) || null,
    // Dean's window, so a PC we cannot sit at still says front, background or fullscreen.
    // A word outside that list is not stored: unknown is not a mode.
    windowMode: (function (w) {
      var s = (w == null) ? '' : String(w);
      return (s === 'front' || s === 'background' || s === 'fullscreen'
              || s === 'headless' || s === 'window-only') ? s : null;
    })(body.windowMode),
    relaunch: (function (r) {
      if (!r || typeof r !== 'object') return null;
      const tri = (v) => (v === true ? true : v === false ? false : null);
      const clip = (v, n) => {
        var s = String(v == null ? '' : v).replace(/\s+/g, ' ').trim()
          .replace(/\b(?:Users|home)[\\/]+(?:[^'"]|'(?=\w))*/gi, '')
          .replace(/(?<![A-Za-z])[A-Za-z]:[\\/](?:[^'"]|'(?=\w))*/g, '')
          .replace(/\\\\[^\s'"]+/g, '')
          .replace(/~[\\/][^\s'"]*/g, '')
          .replace(/\S*\\\S*/g, '')
          .replace(/\s+/g, ' ').trim();
        if (!s || !/[A-Za-z]/.test(s) || /\/Users\/|\/home\/|[A-Za-z]:[\\/](?!\/)|\\/.test(s)) return null;
        return cutAtWord(s, n);
      };
      const head = (v) => (/^[0-9a-f]{4,16}$/.test(String(v == null ? '' : v)) ? String(v) : null);
      const crlf = (v) => (v === 'true' || v === 'false' || v === 'input' || v === 'unset') ? v : null;
      const exit = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null);
      return { armed: tri(r.armed), may: tri(r.may),
               why: cutAtWord(String(r.why == null ? '' : r.why), 160),
               head: head(r.head), autocrlf: crlf(r.autocrlf),
               porcelain: clip(r.porcelain, 240),
               exit: exit(r.exit), err: clip(r.err, 160) };
    })(body.relaunch),
    pull: (function (p) {
      if (!p || typeof p !== 'object') return null;
      const behind = Number(p.behind);
      const clip = (v, n) => {
        var s = String(v == null ? '' : v).replace(/\s+/g, ' ').trim()
          .replace(/\b(?:Users|home)[\\/]+(?:[^'"]|'(?=\w))*/gi, '')
          .replace(/(?<![A-Za-z])[A-Za-z]:[\\/](?:[^'"]|'(?=\w))*/g, '')
          .replace(/\\\\[^\s'"]+/g, '')
          .replace(/~[\\/][^\s'"]*/g, '')
          .replace(/\S*\\\S*/g, '')
          .replace(/\s+/g, ' ').trim();
        if (!s || !/[A-Za-z]/.test(s) || /\/Users\/|\/home\/|[A-Za-z]:[\\/](?!\/)|\\/.test(s)) return null;
        return cutAtWord(s, n);
      };
      const head = (v) => (/^[0-9a-f]{4,16}$/.test(String(v == null ? '' : v)) ? String(v) : null);
      const crlf = (v) => (v === 'true' || v === 'false' || v === 'input' || v === 'unset') ? v : null;
      const exit = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null);
      return { can: (p.can === true ? true : p.can === false ? false : null),
               behind: Number.isFinite(behind) && behind >= 0 ? Math.min(behind, 100000) : null,
               why: cutAtWord(String(p.why == null ? '' : p.why), 160),
               head: head(p.head), autocrlf: crlf(p.autocrlf),
               porcelain: clip(p.porcelain, 240),
               exit: exit(p.exit), err: clip(p.err, 160) };
    })(body.pull),
    // v2163 — WHAT THIS MACHINE HAS, so the fleet roster can show each person's progress on
    // hover of their name. Konyo asked for his cousin's and his wife's live chronicle numbers.
    //
    // ⚠ THE CLIENT SHIPPED THIS FIELD IN v2157 AND NOTHING HERE STORED IT. A cross-family review
    // found it: the beacon posted `tally`, this worker built `rec` from a fixed key list, and the
    // field was dropped on arrival — so the tooltip could never have had data no matter how well
    // the console computed it. Built on both ends, never joined, and silent by construction.
    // [[plumbing-with-no-tap]]
    //
    // COUNTS ONLY, and shaped here rather than trusted: numbers are clamped and anything that is
    // not a number becomes null. No item names ever cross this boundary — a roster says how many,
    // never which. The client already omits the field entirely when its board was unreadable, so
    // absent means "not reported", never zero.
    tally: (function (t) {
      if (!t || typeof t !== 'object') return null;
      const pair = (p) => {
        if (!p || typeof p !== 'object') return null;
        const have = Number(p.have);
        const total = Number(p.total);
        if (!Number.isFinite(have) || have < 0) return null;
        return { have: Math.min(have, 100000),
                 total: (Number.isFinite(total) && total > 0) ? Math.min(total, 100000) : null };
      };
      const at = Number(t.at);
      // ⚠ v2168 — CARRY `ok`. The tooltip reads `if (!t || !t.ok)` and renders "no counts
      // reported yet", so a record stored WITHOUT that field failed the test and the feature
      // stayed invisible even though the numbers had arrived intact. Third joint of the same
      // feature to be built on both ends and not joined; found by a review lens.
      // ⚠ v2188 — AND CARRY THE REFUSAL. `ok: true` was hardcoded and a tally with no pairs
      // returned null, so a machine that CANNOT count was indistinguishable from one that never
      // reported — and the tooltip is built to render `t.why`. That is the FOURTH joint of this
      // one feature built on both ends and not joined (this comment said "third"). A refusal
      // carries no item data: a short reason string and nulls. [[the-unjoined-end]]
      // ⚠⚠ v2741 — THE FIFTH JOINT OF THIS ONE FEATURE, and the three comments above already
      // describe the other four. v2739/v2740 compute `onOwnerSeed` on the board and the beacon
      // posts it; this fixed key list dropped it, so the fleet card read a field that could never
      // arrive. Found by an end-to-end chain check, not by a gate — no gate here grades what the
      // worker STORES against what the client SENDS. [[the-unjoined-end]] [[plumbing-with-no-tap]]
      //
      // ⛔ THE BOUNDARY FOUR LINES ABOVE IS KEPT: a boolean crosses, identity strings do not.
      // `ledgerName` and `seedLedger` would name a person's world, neither consumer needs them,
      // and widening a public boundary to make a warning more specific is not a trade this file
      // makes. Shaped, not trusted: anything that is not a real boolean becomes null, and null is
      // UNKNOWN — the card renders nothing for it. Only an explicit `true` shows the warning, so a
      // garbled beacon cannot make a console look clean either way. [[unknown-stays-unknown]]
      const seedProvenance = (t.onOwnerSeedProvenance === 'measured' || t.onOwnerSeedProvenance === 'absent' || t.onOwnerSeedProvenance === 'unreported') ? t.onOwnerSeedProvenance : null;
      const out = { ok: t.ok === true,
                    sets: pair(t.sets), uniques: pair(t.uniques), runewords: pair(t.runewords),
                    onOwnerSeed: (typeof t.onOwnerSeed === 'boolean') ? t.onOwnerSeed : null,
                    onOwnerSeedProvenance: seedProvenance,
                    // ⚠ v2746 — FORWARD THE AUTHORITY VERDICT TOO. v2739 shipped `onOwnerSeed` on
                    // the board and on the card and the SHAPER BETWEEN THEM DROPPED IT, so the
                    // field existed at both ends and never arrived. Adding a second field without
                    // adding it here would repeat that exactly. [[the-unjoined-end]]
                    // Passed through as-is: it is the authority's own object, and re-deriving any
                    // part of it here would make a second opinion nobody reconciles.
                    ledgerVerdict: (t.ledgerVerdict && typeof t.ledgerVerdict === 'object') ? t.ledgerVerdict : null,
                    // ⚠⚠ THE SIXTH JOINT, found by the doctor row "a tally agrees with its own ledger verdict":
                    // v3389 seals `measured` (true / false / null) + `measuredWhy` on every tally, and this key
                    // list dropped both - so every fleet row, v3499 consoles included, arrived with no
                    // `measured` and the row read MISSING for all of them. Tri-state, shaped like onOwnerSeed:
                    // a real boolean crosses, anything else is null = UNKNOWN. [[the-unjoined-end]]
                    measured: (typeof t.measured === 'boolean') ? t.measured : null,
                    measuredWhy: (typeof t.measuredWhy === 'string')
                      ? cutAtWord(t.measuredWhy.replace(/\s+/g, ' ').trim(), 200) : null,
                    // ⚠ #240 — THE SEVENTH JOINT, carried in the same commit that mints it. `measured` is one
                    // bit for a whole row, and one ledger never synced blanked its neighbours; the seal now
                    // answers PER LEDGER. Only the three ledger names cross, each a real boolean or null.
                    measuredBy: (function (m) {
                      if (!m || typeof m !== 'object') return null;
                      const o = {};
                      for (const k of ['sets', 'uniques', 'runewords']) {
                        if (k in m) o[k] = (typeof m[k] === 'boolean') ? m[k] : null;
                      }
                      return Object.keys(o).length ? o : null;
                    })(t.measuredBy),
                    at: Number.isFinite(at) ? at : null };
      if (!out.ok) {
        const why = (typeof t.why === 'string') ? t.why.replace(/\s+/g, ' ').trim() : '';
        return why ? { ok: false, why: cutAtWord(why, 160), at: out.at, onOwnerSeedProvenance: seedProvenance } : null;
      }
      return (out.sets || out.uniques || out.runewords) ? out : null;
    })(body.tally),
    // v2213 — WHICH set pieces each machine holds, as BITS over a roster both machines already
    // have. Konyo asked THE FLEET to cross-reference him against his cousin — "show me what he has
    // that i dont" — and counts cannot answer that: 116 does not subtract from 120 to produce
    // names.
    //
    // ⚠ THE BOUNDARY THIS FILE DECLARES IS KEPT. Four lines above, `tally` says "No item names
    // ever cross this boundary — a roster says how many, never which." A mask honours that: this
    // worker stores an OPAQUE base64url string, never decodes it, and cannot name a single item
    // from it. The roster that gives the bits meaning lives on his machines, and the subtraction
    // happens there.
    //
    // Shape is validated, never trusted: a fingerprint, a length, and a body whose size must match
    // that length. Anything else is dropped whole rather than stored half-understood — a mask
    // decoded against the wrong roster names real items that are simply the wrong ones, and that
    // failure is silent.
    // 167 — is this machine's capture eye live. Boolean + age only; no paths, no reel ids.
    // Absent means the client did not report it. live:false is measured-dark, not missing.
    eye: (function (e) {
      if (!e || typeof e !== 'object') return null;
      const age = Number(e.ageMs);
      const second = (function (s) {
        if (!s || typeof s !== 'object') return null;
        const st = String(s.state || '');
        if (['absent', 'unauthorised', 'off', 'on', 'failing', 'unknown'].indexOf(st) < 0) return null;
        const prov = (typeof s.provider === 'string') ? s.provider.slice(0, 24) : null;
        return prov ? { state: st, provider: prov } : { state: st };
      })(e.second);
      return {
        live: e.live === true,
        // A day is as far as this number is allowed to travel. The console must say "more than
        // a day", not "1440m ago", because the cap is not a measurement.
        ageMs: (Number.isFinite(age) && age >= 0) ? Math.min(age, 86400000) : null,
        ageCapped: Number.isFinite(age) && age >= 86400000,
        second: second,
      };
    })(body.eye),
    // #229 — this machine's OWN system, counts only. A state it does not know becomes null (UNKNOWN),
    // and a reel count that is not a small non-negative integer is null - never a guessed 0.
    system: (function (s) {
      if (!s || typeof s !== 'object') return null;
      const t = String(s.tree == null ? '' : s.tree);
      const r = s.reels;                      // a NUMBER from the beacon; a string '25' is not a count
      const out = {
        tree: ['ok', 'missing', 'unmeasured', 'unknown'].indexOf(t) >= 0 ? t : null,
        reels: (typeof r === 'number' && Number.isInteger(r) && r >= 0 && r <= 100000) ? r : null,
      };
      /* ⚠ 2026-09-28 — HOW THIS PC FILMS D2R (`capture`) AND HOW ITS RIVER DRAINS (`river`). His order:
         "yea add those beacon fields". The console sends both inside `system`; this shaper was the
         whitelist that would have dropped them on arrival — the SEVENTH-JOINT shape `tally` already
         names four times above. Shaped, never trusted: routes and keys from a fixed vocabulary,
         numbers clamped, sentences collapsed, capped and scrubbed of paths/URLs/IPs a second time
         (the console scrubs first; this boundary is PUBLIC). Absent stays ABSENT, so a console
         older than the fields stores exactly what it stored before. [[the-unjoined-end]] */
      /* ⚠ 2026-09-28 — THE USER-FOLDER SEGMENT FIRST. Every path pattern here stops at whitespace and a
         Windows user name routinely holds one: "C:\Users\Dean Smith\tv\x.json" crossed as
         "<path> Smith\tv\x.json" (an adversarial review, reproduced on both sides). `Users|home`, a
         separator, and the NAME up to the next separator or quote (spaces included) become <user>
         BEFORE the generic patterns run — the same pattern as control_app._WIRE_USER_PAT. */
      const txt = function (v, cap) {
        if (typeof v !== 'string') return null;
        /* ⚠ second review round: one OR MORE separators (a repr()-quoted path doubles them), the name runs over
           an apostrophe a letter follows, everything after the user folder up to the closing quote goes with
           it, it runs BEFORE the URL scrub, and a leftover backslash token is a path - control_app._WIRE_USER_PAT. */
        const x = v.replace(/\s+/g, ' ').trim()
          .replace(/\b(?:Users|home)[\\/]+(?:[^'"]|'(?=\w))*/gi, '<user>')
          .replace(/\b[a-z][a-z0-9+.-]*:\/\/\S+/gi, '<url>')
          .replace(/[A-Za-z]:[\\/](?:[^'"]|'(?=\w))*/g, '<path>')
          .replace(/\\\\[^\s'"]+/g, '<path>')
          .replace(/~[\\/][^\s'"]*/g, '<path>')
          .replace(/(^|[^\w.])\/(?:[^\s\/'"]+\/)+[^\s'"]*/g, '$1<path>')
          .replace(/\S*\\\S*/g, '<path>')
          .replace(/\b\d{1,3}(?:\.\d{1,3}){3}\b/g, '<ip>');
        return x ? cutAtWord(x, cap) : null;
      };
      const num = function (v, max) {
        return (typeof v === 'number' && Number.isFinite(v) && v >= 0) ? Math.min(v, max) : null;
      };
      const whole = function (v, max) {
        return (typeof v === 'number' && Number.isInteger(v) && v >= 0 && v <= max) ? v : null;
      };
      const key = function (v) {
        return (typeof v === 'string' && /^[a-z][a-z-]{0,31}$/.test(v)) ? v : null;
      };
      const DAY400 = 400 * 86400;
      if (s.capture && typeof s.capture === 'object') {
        const c = s.capture;
        out.capture = {
          route: ['native', 'boosteroid', 'geforce-now', 'unknown'].indexOf(String(c.route)) >= 0
            ? String(c.route) : null,
          ageS: num(c.ageS, DAY400),
          why: txt(c.why, 200),
          source: ['capture-half', 'finder'].indexOf(String(c.source)) >= 0 ? String(c.source) : null,
        };
      }
      if (s.river && typeof s.river === 'object') {
        const rv = s.river;
        let lanes = null;
        if (rv.lanes && typeof rv.lanes === 'object' && !Array.isArray(rv.lanes)) {
          const o = {};
          for (const k of Object.keys(rv.lanes).slice(0, 24)) {
            const v = whole(rv.lanes[k], 100000);
            if (/^[A-Z][A-Z_]{0,23}$/.test(k) && v !== null) o[k] = v;
          }
          lanes = Object.keys(o).length ? o : null;
        }
        /* REG-1775 (#86 gap 14) — unknown (the router could not place them) and shelf (the
           denominator) ride beside the station map. Absent stays absent: an older console, and a
           count that is not a whole number, are not zero. The cap is the same one reels uses. */
        const unk = whole(rv.unknown, 100000);
        const shelfN = whole(rv.shelf, 100000);
        let tri = null;
        const x = rv.triage;
        if (x && typeof x === 'object') {
          if (x.ok === false) {
            tri = { ok: false, why: txt(x.why, 200) };
          } else {
            const sk = {};
            if (x.skips && typeof x.skips === 'object') {
              for (const k of Object.keys(x.skips).slice(0, 24)) {
                const v = whole(x.skips[k], 100000000);
                if (key(k) && v !== null) sk[k] = v;
              }
            }
            tri = {
              ok: true,
              lastKey: key(x.lastKey),
              lastWhy: txt(x.lastWhy, 200),
              lastTs: whole(x.lastTs, 1e14),
              sinceLastS: num(x.sinceLastS, DAY400),
              backlog: whole(x.backlog, 100000),
              owedSince: whole(x.owedSince, 1e14),
              owedForS: num(x.owedForS, DAY400),
              waitS: num(x.waitS, DAY400),
              // 2026-09-28 — how long the lane has stood aside for an UNBROKEN run of his game
              playingForS: num(x.playingForS, DAY400),
              ticks: whole(x.ticks, 1e9),
              skips: sk,
            };
          }
        }
        out.river = { lanes: lanes, ageS: num(rv.ageS, DAY400), why: txt(rv.why, 200), triage: tri };
        if (unk !== null) out.river.unknown = unk;
        if (shelfN !== null) out.river.shelf = shelfN;
        /* #74 (REG-1461) — WHICH STATIONS ARE NOT DRAINING ON THAT PC, AND WHY; AND WHETHER IT HAS PROVED ITSELF.
           His ask 2026-09-29: see Dean's river from his own console. Shaped like everything above: station keys
           from the router's vocabulary, counts and ages clamped, the lane's sentence capped and scrubbed. `stuck`
           null (the console could not read its stamp log) stays null - never an empty "flowing" list; absent
           stays absent, so an older console stores exactly what it stored before. */
        if (Array.isArray(rv.stuck)) {
          out.river.stuck = rv.stuck.slice(0, 6).map(function (e) {
            if (!e || typeof e !== 'object') return null;
            const st = String(e.station || '');
            if (!/^[A-Z][A-Z_]{0,23}$/.test(st)) return null;
            const row = { station: st, n: whole(e.n, 100000), oldestS: num(e.oldestS, DAY400), why: txt(e.why, 200) };
            // A reel outside the newest window. Absent means inside, which is what an older build sent.
            if (e.window === false) row.window = false;
            return row;
          }).filter(Boolean);
          // The window this console tallied. Absent on an older build, which measured the whole shelf.
          const keep = whole(rv.stuckKeep, 10000);
          if (keep !== null && keep >= 1) out.river.stuckKeep = keep;
        } else if (rv.stuck === null) {
          out.river.stuck = null;
        }
        if (rv.heart && typeof rv.heart === 'object') {
          const hc = String(rv.heart.census == null ? '' : rv.heart.census);
          out.river.heart = {
            census: ['current', 'stale', 'missing', 'unreadable', 'unknown'].indexOf(hc) >= 0 ? hc : null,
            key: key(rv.heart.key),
            blind: whole(rv.heart.blind, 10000),
          };
        }
      }
      return out;
    })(body.system),
    masks: (function (m) {
      if (!m || typeof m !== 'object') return null;
      const one = (x) => {
        if (!x || typeof x !== 'object') return null;
        const v = String(x.v || '').slice(0, 32);
        const n = Number(x.n);
        const b = String(x.b || '');
        if (!v || !Number.isInteger(n) || n <= 0 || n > 4096) return null;
        if (!b || b.length > 4096 || !/^[A-Za-z0-9_-]+$/.test(b)) return null;
        // base64url of ceil(n/8) bytes, unpadded — a body that does not match its own declared
        // length is a partial read, and a partial read of a bitmask is a wrong answer
        if (b.length > Math.ceil((Math.ceil(n / 8) + 2) / 3) * 4) return null;
        const out = { v: v, n: n, b: b };
        const have = Number(x.have);
        if (Number.isInteger(have) && have >= 0 && have <= n) out.have = have;
        return out;
      };
      /* ⚠⚠ v2460 — THIS STORED ONLY `sets`, AND THAT IS THE OTHER HALF OF REG-357.
         Grok measured that no machine on the fleet has ever published a uniques mask and I
         confirmed it from the live record. Both of us were looking at the board. THIS LINE would
         have thrown a uniques mask away on arrival even if a board had published one — the
         validator above is already ledger-agnostic and the caller (`_masks_for_wire`) has said
         "every ledger this machine can build, not a hardcoded one" since v2329. One end was
         generalised and the other was left naming a single ledger, so the uniques cross-reference
         could never have worked end to end no matter what the boards did.
         The allow-list stays an allow-list — a client cannot invent ledgers — it is just no
         longer one entry long. [[the-unjoined-end]] [[copy-drift]] */
      const LEDGERS = ['sets', 'uniques'];
      const out = {};
      for (const k of LEDGERS) {
        const v = one(m[k]);
        if (v) out[k] = v;
      }
      return Object.keys(out).length ? out : null;
    })(body.masks),
    /* N-3 (Grok) — WHICH LINK GAVE UP, for a ledger that was omitted. He built the producer in
       control_app and nothing here stored it, so it vanished on arrival and every surface
       downstream stayed silent however correct the console was. The reachability gate refused the
       push for exactly this, which is the gate doing its job on a joint built at one end.
       Values are short strings the console writes about ITSELF — never an item name. */
    maskWhy: (function (w) {
      if (!w || typeof w !== 'object') return null;
      const out = {};
      for (const k of ['sets', 'uniques']) {
        const v = w[k];
        if (typeof v === 'string' && v) out[k] = cutAtWord(v, 160);
      }
      return Object.keys(out).length ? out : null;
    })(body.maskWhy),
    /* #41 rank 22 (REG-1564) — WHAT THAT PC'S CHARACTER PICKER OFFERS FOR THE BODY ARMOR SLOT, BESIDE WHAT ITS OWN
       DATABASE HOLDS. The console posts it (`_picker_for_wire`) and, without this line, this fixed key list would
       have dropped it on arrival - the seventh-joint shape `tally` names four times above, and the reason this
       shaper is written in the same commit as the field. Shaped, never trusted: counts are whole numbers clamped,
       the slot and the type are short words, the label and the why are collapsed and capped, `ok` is a real true or
       it is false, and an `ok` census that arrives without its counts is turned to ok:false with a why rather than
       stored as an agreement nobody counted. Absent stays absent (null), so an older console's record keeps its
       shape and the card says "an older build" rather than inventing a census. [[the-unjoined-end]]
       [[unknown-stays-unknown]] */
    picker: (function (p) {
      if (!p || typeof p !== 'object') return null;
      const whole = (v, max) => (typeof v === 'number' && Number.isInteger(v) && v >= 0 && v <= max) ? v : null;
      const num = (v, max) => (typeof v === 'number' && Number.isFinite(v) && v >= 0) ? Math.min(v, max) : null;
      const word = (v) => (typeof v === 'string' && /^[a-z][a-z0-9]{1,11}$/.test(v)) ? v : null;
      const txt = (v, cap) => (typeof v === 'string' && v.trim()) ? cutAtWord(v.replace(/\s+/g, ' ').trim(), cap) : null;
      const out = {
        ok: p.ok === true,
        slot: word(p.slot), type: word(p.type), label: txt(p.label, 40),
        offers: whole(p.offers, 100000), holds: whole(p.holds, 100000), all: whole(p.all, 100000),
        ageS: num(p.ageS, 400 * 86400),
        why: txt(p.why, 200),
        /* true only when THAT PC's board counted and reported a failure - a measured broken picker, not "nothing
           handed over yet"; a card warns on it instead of folding it into UNKNOWN (h22 verifier, 2026-09-30) */
        broken: p.ok !== true && p.broken === true,
      };
      if (out.ok && (out.offers === null || out.holds === null || !out.slot)) {
        out.ok = false;
        out.why = out.why || 'the census arrived without its counts';
      }
      return out;
    })(body.picker),
    /* #93 — THE SHADOW READER, FOR THE EYE ON EVERY FLEET ROW. His switch (on), whether that PC can read at all
       (available), whether a reel is rolling (recording) and whether its watcher is alive (working - that PC's own
       liveness verdict, decided on its own clock). Shaped like picker: booleans stay true/false/null (null = that PC
       could not say), the age is clamped, the words capped. Absent stays null, so an older console draws the UNKNOWN
       eye rather than a guessed one. [[unknown-stays-unknown]] */
    shadow: (function (s) {
      if (!s || typeof s !== 'object') return null;
      const tri = (v) => (v === true ? true : (v === false ? false : null));
      return {
        on: s.on === true, available: tri(s.available), recording: s.recording === true, working: tri(s.working),
        beatAgeS: (typeof s.beatAgeS === 'number' && Number.isFinite(s.beatAgeS) && s.beatAgeS >= 0)
          ? Math.min(s.beatAgeS, 400 * 86400) : null,
        why: (typeof s.why === 'string' && s.why.trim()) ? cutAtWord(s.why.replace(/\s+/g, ' ').trim(), 160) : null,
      };
    })(body.shadow),
    /* v3850 (Elad 17:53) - the recorder's lease: alive + its last renewal. fleet_presence reads it - a live recorder
       keeps a PC online ("online · recording") while its console is down. Absent stays null. */
    recorder: (function (r) {
      if (!r || typeof r !== 'object') return null;
      const ms = typeof r.t === 'string' ? Date.parse(r.t) : NaN;
      return {
        alive: r.alive === true,
        pid: (Number.isInteger(r.pid) && r.pid > 0) ? r.pid : null,
        t: (Number.isFinite(ms) && ms <= Date.now() + 60000) ? new Date(ms).toISOString() : null,
      };
    })(body.recorder),
    /* #108 — THAT PC's TWO READERS (CLAUDE primary, GROK shadow): can each read there? His question, 2026-09-30, after
       the ALT read nothing for a day signed out: "maybe this happened to dean too?". Shaped like shadow: a state is
       on / off, anything else is 'unknown'; needsLogin is true only when that PC said so; the reason capped. Absent
       stays null, so an older console reads UNKNOWN on the card, never a guessed lamp. [[unknown-stays-unknown]] */
    readers: (function (r) {
      if (!r || typeof r !== 'object') return null;
      const lamp = (x) => {
        if (!x || typeof x !== 'object') return { state: 'unknown', needsLogin: false, why: null };
        return {
          state: (x.state === 'on' || x.state === 'off') ? x.state : 'unknown',
          needsLogin: x.needsLogin === true,
          why: (typeof x.why === 'string' && x.why.trim()) ? cutAtWord(x.why.replace(/\s+/g, ' ').trim(), 160) : null,
        };
      };
      return { claude: lamp(r.claude), grok: lamp(r.grok) };
    })(body.readers),
    ip: request.headers.get('CF-Connecting-IP') || '',
    country: cf.country || '',
    city: cf.city || '',
  };

  // v1596 — beacon HONESTY. The client's beacon is fire-and-forget behind a bare
  // `except Exception: pass`, so a machine whose beacon has failed every time for months
  // looks IDENTICAL to a machine nobody ever turned on. The app now reports the PREVIOUS
  // attempt's outcome here; we store it so Konyo can SEE "this machine tried and failed"
  // instead of inferring silence. Absent is normal — older builds do not send it.
  const lastBeacon = coerceLastBeacon(body.lastBeacon);
  if (lastBeacon) rec.lastBeacon = lastBeacon;

  /* ⚠ 2026-09-28 — THE AGES IN `system` ARE AS OF THIS RECORD, AND THE RECORD SAYS WHEN THAT WAS.
     capture.ageS, river.ageS, river.triage.waitS / owedForS / sinceLastS / playingForS are measured
     by the console at the moment it posts. This worker rewrites the stored record only on a
     material change or every REFRESH_S (900 s), and the console's /api/fleet caches the roster 60 s
     (staleAgeS), so a reader can see an age up to ~16 minutes younger than the thing it describes.
     `system.asOf` is the record time (= rec.t, THIS worker's clock): the true age of any of those
     fields is  ageS + (now - asOf)  — with `now` taken from GET /api/console's own `now` (the same
     clock, no skew between machines) plus the console's staleAgeS. Stamped only when the block
     carries an age, so an older console's record keeps exactly the shape it always had.
     [[stale-reading]] */
  if (rec.system && (rec.system.capture || rec.system.river)) rec.system.asOf = rec.t;

  const stored = [];
  const skipped = [];

  /* ══ v2283 — THE ROSTER WAS DYING EVERY DAY AT A DIFFERENT HOUR ═══════════════════════════════
     Konyo: "i dont see anyone online in fleet. and all three consoles are definitely live right
     now. it say slast seen 2h".

     They were all live. This function was returning HTTP 500 (Cloudflare 1101 — the Worker
     throwing) on every POST while GET answered 200, so all three machines froze at the same
     instant and the panel called them offline.

     ROOT CAUSE, MEASURED, NOT GUESSED. Each heartbeat did TWO kv.put calls, every ~4 minutes, per
     machine: 3 x 15/hr x 2 = ~2,160 writes/day against Cloudflare KV's free-tier ceiling of 1,000
     writes/day. Once spent, kv.put throws and the whole request 500s. Reads are on a far larger
     limit, which is exactly why GET kept working.
     PROVEN by a falsifiable prediction: a POST at 2026-08-29T23:58:52Z returned 500 and the same
     POST at 00:01:29Z — ninety seconds after the UTC quota reset — returned 200.

     TWO CHANGES, and the second matters more than the first:
     1. WRITE LESS. Presence is refreshed at most every REFRESH_S, with the TTL widened to cover
        two missed refreshes, and the durable last-seen is rewritten only when something about the
        machine ACTUALLY CHANGED. A heartbeat that says exactly what the last one said is not news
        and does not need to be spent on. Worst case now ~540 writes/day for three machines.
     2. FAIL HONESTLY. A quota refusal is no longer allowed to become a 500. It answers ok:false
        with a reason the console can render, because "the roster would not take my beacon" and
        "that machine is gone" are opposite facts and the panel had been printing the second one
        for the first. [[unknown-stays-unknown]] */
  /* ⚠ THESE TWO NUMBERS ARE A BUDGET, NOT A TASTE. My first cut used 480s and the guard that
     computes the worst case rejected it: 3 machines x (3600/480) x 24 x 2 keys = 1,080 writes/day,
     still over the 1,000/day ceiling. The optimistic figure (lastseen only on change) is about
     half that — but a budget must be sized on the worst case, or it fails on the one day
     everything changes at once. At 900s with room for a FOURTH machine:
       4 x (3600/900) x 24 x 2 = 768 writes/day, comfortably under 1,000.
     Presence is then accurate to within 15 minutes, which is the right trade: a fleet panel that
     is coarse beats a roster that dies at a different hour every day. */
  const REFRESH_S = 900;          // rewrite presence at most every 15 minutes
  const PRESENCE_TTL = 2400;      // ...and let it live 40, so two missed refreshes do not evict

  let prevRaw = null;
  try { prevRaw = await kv.get('console:' + machine); } catch (e) { prevRaw = null; }
  let prev = null;
  try { prev = prevRaw ? JSON.parse(prevRaw) : null; } catch (e) { prev = null; }

  // A presence patch is a window or shadow change. Building the whole status under a game
  // took long enough that a close showed up on the fleet minutes late. The console resends
  // the last full beacon with the live window and shadow and presenceOnly set, so a worker
  // that does not know this flag still stores a whole row. This worker keeps the stored row
  // and overlays the window, the shadow, the time, and event hb. The measurement clock
  // (system.asOf) stays the time those ages were taken. No stored row means there is nothing
  // to overlay, and the console then sends a full beacon. event is hb so a change does not
  // also write a consolelog row.
  /* v3850 - a recorderOnly patch is sent by the keepalive while the console is DOWN. It overlays ONLY the recorder:
     the console's own `t` is kept, so the row never reads as a fresh console heartbeat. */
  if (body.recorderOnly === true) {
    if (!prev || typeof prev !== 'object') {
      return json({ ok: true, machine, stored: [], skipped: ['recorder patch with no row yet'] }, 200);
    }
    const mergedR = Object.assign({}, prev, { recorder: rec.recorder, event: 'hb' });
    for (const k of Object.keys(rec)) delete rec[k];
    Object.assign(rec, mergedR);
  }
  const presenceOnly = body.presenceOnly === true;
  if (presenceOnly) {
    if (!prev || typeof prev !== 'object') {
      return json({ ok: true, machine, stored: [], skipped: ['presence patch with no row yet'] }, 200);
    }
    const merged = Object.assign({}, prev, {
      t: rec.t,
      windowMode: rec.windowMode,
      shadow: rec.shadow,
      event: 'hb',
    });
    for (const k of Object.keys(rec)) delete rec[k];
    Object.assign(rec, merged);
  }

  const ageS = (prev && prev.t) ? ((Date.now() - Date.parse(prev.t)) / 1000) : 1e9;
  // ⚠ MATERIAL means "a thing he reads on the panel". Two heartbeats that differ only in their
  // timestamp are the same news, and news is what a write is for.
  // ⚠ 2026-09-28 — WHICH WAY A PC FILMS D2R IS NEWS. Without it a PC that switched from its native
  // game to a Boosteroid stream kept the OLD route on the fleet for up to REFRESH_S (15 min), with an
  // ageS that described the old pin. The route is a word from a fixed vocabulary, so it changes only
  // when the capture really moved — a write per switch, not per heartbeat. The ages (ageS, waitS)
  // are NOT material: they move every beacon, and a reader adds (now - system.asOf) instead.
  const capRoute = (r) => (r && r.system && r.system.capture && r.system.capture.route) || null;
  // #41 rank 22 — WHAT A PC'S PICKER OFFERS IS PRINTED ON THE PANEL, so a change to it is news (h22 verifier: a
  // census-only change 45/45 -> 40/45 wrote NOTHING for up to REFRESH_S). The counts, the slot, ok and broken are
  // compared; its age is not (it moves every beacon; a reader adds now - asOf), exactly as capRoute does.
  // #93 — whether a PC's shadow reader is on and WORKING is what the fleet's eye shows, so a flip is news; the beat's
  // age is not (it moves every tick) - that PC decides `working` on its own clock before it posts.
  const shadowNews = (r) => {
    const x = r && r.shadow;
    return (x && typeof x === 'object') ? JSON.stringify([x.on, x.available, x.recording, x.working]) : null;
  };
  // #108 — a reader that stops (or starts) reading on a PC is what its row says, so a flip is news; the reason's words
  // are not (the ok counts inside it move every read).
  const readersNews = (r) => {
    const x = r && r.readers;
    return (x && typeof x === 'object')
      ? JSON.stringify([x.claude && x.claude.state, x.claude && x.claude.needsLogin, x.grok && x.grok.state,
                        x.grok && x.grok.needsLogin])
      : null;
  };
  // REG-1734 — WHETHER A PC'S RIVER IS STUCK IS PRINTED ON EVERY OTHER PC'S ROW ("river stuck"), so a flip is news.
  // MEASURED 2026-10-02: his Mac's river was clear on its own console while his Windows ALT still drew the Mac "river
  // stuck" - the stored record only refreshed every REFRESH_S (15 min), because `stuck` was not compared here. The
  // stations and their counts are compared; the ages are not (they move every beacon). null (cannot read) vs []
  // (measured clear) is a flip too.
  // REG-1771 (#86 gap 11, the half that comparison left) — the row's "locks shut" is river.heart.census, and the
  // click box names the lane counts and the triage word (last outcome, owed). None of those were compared, so a
  // census that went missing, or a river that filled, kept the previous sentence for up to REFRESH_S. Ages, skip
  // counts and the lane key are still not news. A stuck key that was never sent is not a stuck list that arrived
  // null: the card reads one as an older build and the other as unreadable.
  const riverNews = (r) => {
    const rv = r && r.system && r.system.river;
    if (!rv || typeof rv !== 'object') return null;
    let stuckWord;
    if ('stuck' in rv) {
      const sk = rv.stuck;
      const keep = (typeof rv.stuckKeep === 'number') ? rv.stuckKeep : null;
      stuckWord = Array.isArray(sk)
        ? [keep, sk.map((e) => [e && e.station, e && e.n, e && e.window === false])]
        : sk;
    }
    const h = (rv.heart && typeof rv.heart === 'object') ? rv.heart : null;
    // #193 (his Fleet, 2026-10-28: Dean "says STarting it could be stale") - the row prints two of the prover's keys as
    // words ('river · starting', 'census waiting for memory'), so those two are news; the others move each slice and are not.
    const heartWord = h ? [h.census, (typeof h.blind === 'number') ? h.blind : null,
                           (h.key === 'starting' || h.key === 'low-memory') ? h.key : null] : null;
    let laneWord = null;
    if (rv.lanes && typeof rv.lanes === 'object' && !Array.isArray(rv.lanes)) {
      laneWord = Object.keys(rv.lanes).sort().map((k) => [k, rv.lanes[k]]);
    } else if (rv.lanes === null) laneWord = 'none';
    const t = (rv.triage && typeof rv.triage === 'object') ? rv.triage : null;
    const triageWord = t
      ? [t.ok === false, t.lastKey || null, (typeof t.backlog === 'number') ? t.backlog : null]
      : null;
    // REG-1775 (#86 gap 14) — the river line names unplaced and the gap against the shelf, so a
    // change in either count is news. An age is not. Absent is not a measured zero.
    const placeWord = [
      (typeof rv.unknown === 'number') ? rv.unknown : null,
      (typeof rv.shelf === 'number') ? rv.shelf : null,
    ];
    const placeSaid = placeWord[0] !== null || placeWord[1] !== null;
    if (stuckWord === undefined && heartWord === null && laneWord === null && triageWord === null
        && !placeSaid) return null;
    return JSON.stringify([stuckWord === undefined ? 'absent' : stuckWord, heartWord, laneWord,
                           triageWord, placeWord]);
  };
  // REG-1771 — the hover says whether that PC's own tree is established, and how many reels sit on its shelf.
  // Both flip rarely (a reel is added, a tree goes missing). They are not ages.
  const shelfNews = (r) => {
    const s = r && r.system;
    if (!s || typeof s !== 'object') return null;
    if (!('tree' in s) && !('reels' in s)) return null;
    return JSON.stringify([
      ('tree' in s) ? s.tree : 'absent',
      (typeof s.reels === 'number') ? s.reels : null,
    ]);
  };
  // REG-1771 — an offline row says "roster refused its beacon" from lastBeacon.ok, with the code. The attempt
  // clock (`t`) moves on every post, so it is not news.
  const beaconNews = (r) => {
    const b = r && r.lastBeacon;
    if (!b || typeof b !== 'object' || !('ok' in b)) return null;
    return b.ok === false ? ('refused:' + (b.code == null ? '' : b.code)) : 'ok';
  };
  const pickerNews = (r) => {
    const p = r && r.picker;
    return (p && typeof p === 'object') ? JSON.stringify([p.ok, p.slot, p.offers, p.holds, p.broken]) : null;
  };
  const material = !prev
    || prev.ver !== rec.ver || prev.mode !== rec.mode || prev.event !== rec.event
    || prev.diskVer !== rec.diskVer
    || prev.windowMode !== rec.windowMode
    || JSON.stringify(prev.tally || null) !== JSON.stringify(rec.tally || null)
    || JSON.stringify(prev.masks || null) !== JSON.stringify(rec.masks || null)
    || JSON.stringify(prev.relaunch || null) !== JSON.stringify(rec.relaunch || null)
    || JSON.stringify(prev.pull || null) !== JSON.stringify(rec.pull || null)
    || capRoute(prev) !== capRoute(rec)
    || riverNews(prev) !== riverNews(rec)
    || shelfNews(prev) !== shelfNews(rec)
    || beaconNews(prev) !== beaconNews(rec)
    || pickerNews(prev) !== pickerNews(rec)
    || shadowNews(prev) !== shadowNews(rec)
    || readersNews(prev) !== readersNews(rec)
    || !!(prev.eye && prev.eye.live) !== !!(rec.eye && rec.eye.live);

  try {
    if (material || ageS >= REFRESH_S) {
      await kv.put('console:' + machine, JSON.stringify(rec), { expirationTtl: PRESENCE_TTL });
      stored.push('console');
    } else {
      skipped.push('console (unchanged, refreshed ' + Math.round(ageS) + 's ago)');
    }

    // ⚠⚠ v3390 (#135) — THE LAST CHECK-IN, NOT THE LAST CHANGE. Until now this read
    // `if (material)`, so a console that was OPEN and beaconing every ~4 minutes with nothing
    // moving never refreshed this key. MEASURED: Konyo watched Dean in the console app while
    // this row said 26h, and an idle repeat beacon against the real handler stores NOTHING.
    // Dean's row froze hardest precisely because he is the least busy user.
    // ⚠ THE HEADER OF THIS FILE ALREADY PROMISED THIS ("written on EVERY beacon INCLUDING
    // heartbeats") and the budget above already PAID for it: "4 x (3600/900) x 24 x 2 = 768
    // writes/day" — the x 2 is BOTH keys at the 15-minute cadence. The code was the odd one out.
    // ⚠ Bounded by the SAME REFRESH_S as presence, so the write budget is unchanged from the one
    // that comment computed; this is not a new cost, it is the cost already budgeted.
    if (material || ageS >= REFRESH_S) {
      await kv.put('lastseen:' + machine, JSON.stringify(rec), {
        expirationTtl: 60 * 60 * 24 * 400,  // 400 days
      });
      stored.push('lastseen');
    } else {
      skipped.push('lastseen (nothing changed)');
    }
  } catch (e) {
    /* ⚠ THE WHOLE POINT. A storage refusal must reach him as a REFUSAL, not as a machine that
       vanished. 200 with ok:false so the console can parse it and say UNKNOWN; a 500 here is what
       made three live machines read as offline for two hours. */
    return json({
      ok: false, machine,
      why: 'the roster could not store this beacon — ' + cutAtWord(String((e && e.message) || e), 140),
      hint: 'this is the storage refusing a write, NOT the machine being absent',
      stored, skipped,
    }, 200);
  }

  // event log: boots and mode flips only — heartbeats would bloat the KV
  if (event !== 'hb') {
    await kv.put('consolelog:' + rec.t + ':' + machine, JSON.stringify(rec), {
      expirationTtl: 60 * 60 * 24 * 30,   // 30 days of history
    });
    stored.push('consolelog');
  }

  // Echo enough for the client to record a VERIFIED success rather than merely "no exception
  // was thrown". Never the IP, never a secret — the caller already knows its own machine name.
  let fleet = null;
  try { fleet = (await listAll(kv, 'console:')).length; } catch (e) { fleet = null; }
  return json({ ok: true, machine, recorded: rec.t, stored, fleet });
}

/**
 * v1496 — GET /api/console → the fleet as JSON: who is online now and when each machine was last
 * seen. Konyo: "i want to have a tracker for whose logged in and when.. like we have for the
 * website." /console (the HTML page) already answered that in a browser tab behind a key; this
 * lets the console app itself answer it, so the machine he is sitting at can show its own fleet.
 * Same Basic gate as every other /api route (the app already authenticates for the beacon), and
 * strictly read-only.
 *
 * Shape: { ok, now, scope, online[], offline[] (each offline:true), scan{} }.
 */
export async function onRequestGet(context) {
  const { env } = context;
  const kv = env && env.TZ_HISTORY;
  if (!kv) return json({ ok: false, error: 'storage unavailable' }, 500);

  // v1496 — CI runners used to check in from every test job, so the fleet listed a GitHub VM in
  // Boydton beside Konyo's MacBook. The beacon no longer sends from CI, but entries already in KV
  // (and any older build still running) are filtered here too — belt and braces, because the answer
  // to "who is online" must only ever contain machines that are his. Applied to presence, lastseen
  // and consolelog alike.
  const isRunner = (m) => /^runnervm|^fv-az|^runner-/i.test(String((m && m.machine) || ''));
  const readAll = async (keys) => (await Promise.all(
    keys.map((k) => Promise.resolve(kv.get(k.name, 'json')).catch(() => null)),
  )).filter(Boolean).filter((m) => m && m.machine).filter((m) => !isRunner(m)).sort(newestFirst);

  // presence — 'console:' cannot match a 'consolelog:' key (see REFUTED note in the header).
  const presenceKeys = await listAll(kv, 'console:');
  const machines = await readAll(presenceKeys);

  // `seen` is seeded from ONLINE: an online machine's own history is deliberately suppressed,
  // because it is already reported above with a live record. Dedupe is strict string equality
  // on l.machine — never a prefix or normalised name, or one machine would eat another's row.
  const seen = new Set(machines.map((m) => m.machine));
  const offline = [];
  const take = (list) => {
    for (const l of list) {
      if (seen.has(l.machine)) continue;
      seen.add(l.machine);
      offline.push({ ...l, offline: true });
    }
  };

  // PRIMARY offline source: the durable last-seen keys. One key per machine, 400-day TTL —
  // there is no window for a recent machine to fall out of.
  const lastseenKeys = await listAll(kv, 'lastseen:');
  take(await readAll(lastseenKeys));

  // SECONDARY backfill: the event log, for machines that last beaconed BEFORE lastseen: shipped
  // and therefore have no durable key yet. Full cursor pagination — the old limit:400 here read
  // the OLDEST 400 events and is what made recent machines invisible.
  //
  // v1597.1 — machine + time come from the KEY NAME (see machinesFromLogKeys). Reading all 2,556
  // values blew the per-invocation subrequest cap and 500'd the page. Only the newest event of
  // each machine we are actually going to SHOW gets fetched, which is a handful of reads.
  const logKeys = await listAll(kv, 'consolelog:');
  const logMachines = machinesFromLogKeys(logKeys)
    .filter((m) => !seen.has(m.machine))
    .filter((m) => !isRunner(m))
    .sort(newestFirst)
    .slice(0, 40);                                   // a bounded, stated cap — not a silent one
  const logDetail = (await Promise.all(logMachines.map((m) =>
    Promise.resolve(kv.get(m.key, 'json')).catch(() => null))))
    .map((rec, i) => (rec && rec.machine ? rec : logMachines[i]));   // fall back to key-derived
  take(logDetail.filter(Boolean).filter((m) => !isRunner(m)));

  offline.sort(newestFirst);

  // ── v3387 — THE SECOND DOOR, JOINED TO THE FIRST ────────────────────────────────────────
  // Konyo: "make sure to join them so there is not mismatch and unsycn between them so they
  // match and work as a one visual read."
  //
  // Until now this endpoint answered ONE question — when did the console APP last beacon — and
  // the rail printed that age with no statement of what it was the age of. A person who had
  // been reading the bible in a browser an hour ago showed as last seen days back, truthfully
  // and uselessly. `webseen:<slug>` (written by recordVisit in functions/_middleware.js) is the
  // other half: one durable key per web identity, affordable to read here.
  //
  // ⚠ THE MATCH IS EXACT OR IT DOES NOT HAPPEN. A web identity is attached to a machine row only
  // when its slug equals the slug of that row's own user / nickname / machine. Nothing fuzzy,
  // no prefixes, no "looks like the same person" — inventing a link here would put one person's
  // presence on another person's row, which is a worse lie than the silence it replaces.
  // [[unknown-stays-unknown]]
  //
  // ⚠ AND AN UNMATCHED IDENTITY IS NEVER DROPPED. It goes to webOnly[] — somebody who reads the
  // bible and has never run the console is a real person the fleet has always been blind to.
  // They are kept OUT of online[]/offline[] on purpose: those are lists of MACHINES, and the
  // console's own fleet_drop_non_machines() correctly discards anything with no install id.
  const webKeys = await listAll(kv, 'webseen:');
  const web = (await Promise.all(webKeys.map((k) =>
    Promise.resolve(kv.get(k.name, 'json')).catch(() => null))))
    .filter((w) => w && w.t)
    .sort(newestFirst);

  const byIdent = new Map();
  for (const w of web) {                       // web[] is newest-first, so the first wins
    const s = w.slug || webSeenSlug(w.user);
    if (!byIdent.has(s)) byIdent.set(s, w);
  }

  // ISO-8601 sorts lexicographically in chronological order, which is the property every epoch
  // cut in this codebase leans on. Either side may be absent, and absent is not "older".
  const newerOf = (a, b) => {
    const A = a ? String(a) : '', B = b ? String(b) : '';
    if (!A) return B || null;
    if (!B) return A;
    return A >= B ? A : B;
  };

  const claimed = new Set();
  for (const row of machines.concat(offline)) {
    let hit = null, via = null;
    for (const field of ['user', 'nickname', 'machine']) {
      const s = webSeenSlug(row[field]);
      if (s === '_anon') continue;             // an empty field matches the anonymous bucket
      if (byIdent.has(s)) { hit = byIdent.get(s); via = field; break; }
    }
    row.webAt = hit ? hit.t : null;
    row.webVia = via;                          // HOW it matched — null when nothing did
    row.seenAt = newerOf(row.t, row.webAt);
    // Which door produced seenAt. `null` when neither store could answer, never 'console'.
    row.seenVia = !row.seenAt ? null
      : (row.webAt && row.seenAt === row.webAt && row.seenAt !== row.t) ? 'web' : 'console';
    row.seenBoth = !!(row.t && row.webAt);
    if (hit) claimed.add(hit.slug || webSeenSlug(hit.user));
  }

  const webOnly = web.filter((w) => !claimed.has(w.slug || webSeenSlug(w.user)));

  // v1596 — SCAN DIAGNOSTICS. offline:[] used to be unreadable: it could mean "nobody has been
  // here" or "the scan is broken", and those look the same. These counts separate them.
  // pages/complete are derived from key counts because listAll is kept byte-identical across
  // the two console files; complete goes false if the 50-page hard cap could have truncated.
  const pagesFor = (n) => Math.max(1, Math.ceil(n / PAGE_SIZE));
  const scan = {
    logKeys: logKeys.length,
    lastseenKeys: lastseenKeys.length,
    presenceKeys: presenceKeys.length,
    pages: pagesFor(presenceKeys.length) + pagesFor(lastseenKeys.length) + pagesFor(logKeys.length),
    complete: presenceKeys.length < PAGE_CAP * PAGE_SIZE
      && lastseenKeys.length < PAGE_CAP * PAGE_SIZE
      && logKeys.length < PAGE_CAP * PAGE_SIZE,
  };

  return json({
    ok: true,
    now: new Date().toISOString(),
    scope: 'BOTH doors, joined (v3387). Each machine row carries t = the console APP beacon and webAt = a browser page-view of /d2r/ by the same identity; seenAt is the newer of the two and seenVia names WHICH door it came from. A browser identity no machine row can claim is listed in webOnly[] rather than merged into anybody. Before v3387 this endpoint reported console beacons ONLY, which is why a person reading the bible could show as absent for days.',
    online: machines,
    offline,
    web,
    webOnly,
    scan,
  });
}

function newestFirst(a, b) {
  return String((a && a.t) || '') < String((b && b.t) || '') ? 1 : -1;
}

/**
 * Defensive coercion of the client-reported PREVIOUS beacon result. Anything unexpected is
 * dropped rather than thrown on — a malformed health report must never cost us the beacon.
 */
function coerceLastBeacon(v) {
  try {
    if (!v || typeof v !== 'object' || Array.isArray(v)) return null;
    const out = {};
    if (v.ok !== undefined && v.ok !== null) out.ok = !!v.ok;
    if (v.code !== undefined && v.code !== null && Number.isFinite(Number(v.code))) out.code = Number(v.code);
    if (v.err !== undefined && v.err !== null) out.err = cutAtWord(String(v.err), 120);
    if (v.t !== undefined && v.t !== null) out.t = String(v.t).slice(0, 40);
    return Object.keys(out).length ? out : null;
  } catch (e) { return null; }
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}
