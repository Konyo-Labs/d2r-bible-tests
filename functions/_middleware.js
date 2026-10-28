/**
 * Site-wide HTTP Basic Auth gate (Konyo + cousins, private personal tool).
 *
 * Runs on EVERY request to the Pages project. Only the PASSWORD matters — any
 * username is accepted — so there's a single secret to share. The password lives
 * in the Cloudflare env var SITE_PASS (a secret, never in the repo); if it's not
 * set the gate is OPEN (fail-safe so a missing secret never locks the site out).
 *
 * EXCEPTION: /api/tz is left open so the Telegram alert bot's 5-min recorder ping
 * (which sends no credentials) keeps the 48h history filling 24/7, and the public
 * TZ data stays reachable. Everything else — the bible, art, /api/intake — is gated.
 * The bible page calls /api/intake same-origin, so the browser auto-sends the
 * logged-in credentials; only outside visitors are blocked.
 *
 * VISIT LOG (2026-06-22): every authenticated load of the app page is recorded to
 * the TZ_HISTORY KV store under a `visit:` key (time, IP, city/country, device,
 * login name). View it at /visits?k=<VISITS_KEY>. Logging is best-effort and fully
 * wrapped — it can never delay or block a response (see recordVisit()).
 */
export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);

  // the app lives under /d2r/ — send the bare domain (and /index.html) there so a
  // bookmark of the plain host lands on the app instead of a blank 404.
  if (url.pathname === '/' || url.pathname === '/index.html') {
    return Response.redirect(url.origin + '/d2r/', 308);
  }

  // bot recorder + public TZ endpoint: always open.
  // v1710 — /d2r/api/tz is the same function under the app prefix. The board
  // lives at /d2r/, so a relative fetch (or a host rewrite) used to 401 here
  // while /api/tz was 200. Leave both open; the Pages function for the
  // cousin path lives at functions/d2r/api/tz.js.
  if (url.pathname === '/api/tz' || url.pathname === '/d2r/api/tz') return next();

  // TV DIABLO one-shot installers: must be fetchable with zero credentials
  // (Windows irm|iex + Mac curl|bash). Scripts hold no secrets — public repo.
  if (url.pathname === '/d2r/install-tvd.ps1' || url.pathname === '/d2r/install-tvd.sh') return next();

  // REG-2871 (#83) - the item art a d2jsp post embeds ([img]) must load for a reader who has no password. Only a GET of an
  // image file directly under /d2r/art/ is open; the art is already public in the repo. Everything else stays gated.
  if (request.method === 'GET' && /^\/d2r\/art\/[A-Za-z0-9_.\-]+\.(?:png|jpe?g|gif|webp)$/i.test(url.pathname)
      && url.pathname.indexOf('..') < 0) return next();

  // decode the Basic Auth username — ignored for AUTH, but recorded so Konyo can
  // label who's who (tell a cousin to log in as e.g. "cuz" and visits show it).
  let user = '';
  const header = request.headers.get('Authorization') || '';
  if (header.startsWith('Basic ')) {
    try { const d = atob(header.slice(6)); user = d.slice(0, d.indexOf(':')); } catch (e) { /* ignore */ }
  }

  const SECRET = env && env.SITE_PASS;
  if (!SECRET) {                       // not configured yet → don't lock anyone out
    recordVisit(context, url, user);
    return next();
  }

  if (header.startsWith('Basic ')) {
    let decoded = '';
    try { decoded = atob(header.slice(6)); } catch (e) { decoded = ''; }
    const pass = decoded.slice(decoded.indexOf(':') + 1); // ignore username, check password only
    if (pass === SECRET) {
      recordVisit(context, url, user);
      return next();
    }
  }

  return new Response('🔒 Konyo’s D2R Bible — password required.', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="Konyo D2R Bible", charset="UTF-8"',
      'content-type': 'text/plain; charset=utf-8',
    },
  });
}

/**
 * Best-effort visit recorder. Logs ONLY real loads of the app page (not every art
 * asset / api call), GET only. Any failure is swallowed; the KV write runs in
 * waitUntil so it never adds latency to the user's response.
 */
function recordVisit(context, url, user) {
  try {
    const { request, env } = context;
    if (request.method !== 'GET') return;
    const p = url.pathname;
    if (p !== '/d2r/' && p !== '/d2r/index.html') return; // one log per app page-view
    const kv = env && env.TZ_HISTORY;
    if (!kv) return;

    const cf = request.cf || {};
    const entry = {
      t: new Date().toISOString(),
      user: user || '',
      ip: request.headers.get('CF-Connecting-IP') || '',
      country: cf.country || request.headers.get('CF-IPCountry') || '',
      city: cf.city || '',
      region: cf.region || '',
      ua: request.headers.get('User-Agent') || '',
      ref: request.headers.get('Referer') || '',
    };
    const key = 'visit:' + Date.now() + ':' + Math.random().toString(36).slice(2, 8);
    // keep 90 days, then auto-expire so the log can't grow unbounded
    context.waitUntil(kv.put(key, JSON.stringify(entry), { expirationTtl: 7776000 }).catch(() => {}));
    // v3387 — and the DURABLE per-person key THE FLEET can actually afford to read.
    context.waitUntil(recordWebSeen(kv, entry).catch(() => {}));
  } catch (e) { /* never let logging break the gate */ }
}

/**
 * v3387 — THE DURABLE WEB-PRESENCE KEY, so presence is ONE read instead of two that disagree.
 *
 * Konyo, 2026-09-20: "make sure to join them so there is not mismatch and unsycn between them
 * so they match and work as a one visual read."
 *
 * THE MISMATCH IT CLOSES, stated plainly. THE FLEET reports `lastseen:<machine>` — the console
 * APP beaconing. A browser page-view of /d2r/ lands in `visit:<ms>:<rand>` and is visible only
 * at /visits. So a person who opened the bible six hours ago reads on the fleet rail as last
 * seen whenever their console app last ran, which can be days earlier. MEASURED 2026-09-19/20:
 * Dean's row said 26h while Konyo had watched him on the site that evening. Both numbers were
 * correct. The surface implied they were the same number, and that is the whole defect.
 *
 * ⚠ WHY A NEW KEY AND NOT A SCAN OF `visit:`. The login name lives in the visit VALUE, so
 * grouping page-views by person means reading every one of them. functions/api/console.js
 * already carries the scar from doing exactly that: "Reading all 2,556 values blew the
 * per-invocation subrequest cap and 500'd the page." One durable key per web identity is the
 * same shape `lastseen:` uses against the same problem, and it costs a handful of reads.
 *
 * ⚠ AND IT IS WRITE-THROTTLED. A page-view is cheap to trigger — a reload loop would bill a KV
 * write every time — so the key is rewritten only when the stored stamp is older than
 * WEBSEEN_FLOOR_MS. Worst case per person: 12 writes an hour.
 *
 * 'webseen:' collides with no prefix in use here ('console:', 'consolelog:', 'lastseen:',
 * 'visit:') and is a string-prefix of none of them.
 */
const WEBSEEN_FLOOR_MS = 300000;        // 5 min — the most often one person can cost a write
const WEBSEEN_TTL = 34560000;           // 400 days, matching lastseen: — a person is not forgotten

/**
 * The storage slug for a login name, and THE ONE normaliser both ends of the join use.
 *
 * ⚠ '' IS A REAL CASE, not an error: the Basic gate accepts any username, and with SITE_PASS
 * unset there is no username at all. It becomes '_anon' rather than being dropped, because an
 * unattributable visit is still somebody being here, and discarding it is how a present person
 * reads as absent — the very failure this key exists to end. [[unknown-stays-unknown]]
 *
 * ⚠ EXPORTED ON PURPOSE. functions/api/console.js imports THIS function to normalise the other
 * side of the join. Two copies of a normaliser is how the two console files already shared one
 * bug once (see the listAll note there) — one source, imported. [[copy-drift]]
 */
export function webSeenSlug(user) {
  const u = String(user || '').trim().toLowerCase().replace(/[^a-z0-9._-]/g, '_').slice(0, 24);
  return u || '_anon';
}

async function recordWebSeen(kv, entry) {
  const slug = webSeenSlug(entry.user);
  let prev = null;
  try { prev = await kv.get('webseen:' + slug, 'json'); } catch (e) { prev = null; }
  if (prev && prev.t) {
    const age = Date.parse(entry.t) - Date.parse(prev.t);
    // NaN-safe: an unreadable stored stamp must REWRITE, never suppress. `age !== age` is the
    // NaN test, and a negative age means the stored row is from the future — rewrite both.
    if (age === age && age >= 0 && age < WEBSEEN_FLOOR_MS) return;
  }
  await kv.put('webseen:' + slug, JSON.stringify({
    user: entry.user || '',
    slug,
    t: entry.t,
    ip: entry.ip,
    city: entry.city,
    region: entry.region,
    country: entry.country,
    ua: entry.ua,
  }), { expirationTtl: WEBSEEN_TTL });
}
