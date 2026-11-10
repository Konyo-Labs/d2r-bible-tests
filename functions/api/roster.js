/**
 * POST /api/roster — Fleet 3.0 phase 1, the publish only.
 *
 * This is not the presence beacon. functions/api/console.js keeps its own keys
 * (console:, lastseen:) and its own law: no item name crosses that beacon.
 * A roster row is a different route and a different key, `roster:` plus the
 * owner label (Konyo · Mac, Konyo · ALT, Konyo · GrokBot, Dean, Wife PC).
 * An install id, a hostname, or a path is not a key.
 *
 * v3862 (Workers Paid): presence is budgeted at 4,896 of the fleet's own 10,000
 * KV writes a day (KV_WRITES below). This route adds at most 6 PCs times 25
 * writes (5,046 together). On the free plan it was 768 + 4 x 25 of 1,000.
 * One key per owner, rewritten only when the body changed, at most once an
 * hour, plus one boot publish inside that hour. The 26th write of the UTC
 * day is refused out loud. A refusal is HTTP 200 with ok:false, never a 500
 * that looks like the machine went offline.
 *
 * A section that was not in this body stays as it was, or stays absent.
 * #95 (REG-2516): a signed, verified write keeps a section it did not send only
 * when the stored row was written under the very same key. Anything else the row
 * held - planted unsigned, written before signing, another key's - is dropped, never
 * carried in under this key's "verified".
 * It is never stored as an empty list. Pictures and frame bytes are refused
 * and not stored. GET /api/roster reads every owner label's key and writes nothing.
 * No Roster tab, no D1, no R2.
 *
 * #95 SIGNED PUBLISHING (his ruling 2026-10-22: deploy once the Python/JS signature
 * test passes, trust-on-first-use, never stop a PC from publishing).
 * The site's Basic password is public (the console sends it from a public repo), so
 * it is no longer what lets a row be written. Each PC holds an Ed25519 key
 * (tv/roster_sign.py) and sends X-Roster-Key and X-Roster-Sig (base64url) over the
 * EXACT bytes it posts. Those bytes are verified here with crypto.subtle before they
 * are parsed and before any KV write. Nothing is re-serialised on either side.
 *
 *   no key registered + valid signature  -> the key is registered (rosterkey:<owner>)
 *                                           and the row is stored intentVerified:true
 *   no key registered + unsigned         -> stored intentVerified:false, so a PC that
 *                                           has not updated keeps publishing
 *   no key registered + bad signature    -> stored intentVerified:false and NOT
 *                                           registered: anyone could post that row
 *                                           unsigned, and a signer bug must not stop
 *                                           a PC from publishing. The reply says why.
 *   registered + same key + valid        -> stored intentVerified:true
 *   registered + unsigned, another key,
 *   or a bad signature                   -> refused (200, ok:false) with its own why
 *                                           and hint. Nothing is stored.
 *
 * A key changes only when Konyo deletes rosterkey:<owner> from the Mac. Nothing here
 * changes one by itself. The next signed publish then registers that PC's key:
 *   npx wrangler kv namespace list          (the id of the namespace bound as TZ_HISTORY)
 *   npx wrangler kv key delete "rosterkey:<owner>" --namespace-id=<that id> --remote
 * A key can also be put there before a PC's first publish (pre-seeded):
 *   npx wrangler kv key put "rosterkey:<owner>" '{"pub":"<base64url>","keyId":"<12 hex>","at":0}' --namespace-id=<that id> --remote
 * A row stored before signing has no intentVerified. GET passes the field only when
 * the record holds a boolean, so a viewer shows that row UNKNOWN, never verified.
 */

/* v3862 - WORKERS PAID (confirmed 2026-11-05). KV_WRITES is this fleet's OWN daily ceiling, a third of what the plan
   includes (1,000,000 a month ~ 32,000 a day), sized for six PCs: presence 4,896 (console.js REFRESH_S) + roster
   6 x 25 + profile 6 x PROFILE_DAY_CAP + frames 6 x FRAMES_DAY_CAP. On the free plan it was 1,000. */
const PRESENCE_WRITES = 4896;
const ROSTER_PCS = 6;
const ROSTER_CAP = 25;
const KV_WRITES = 10000;
const HOUR_MS = 3600 * 1000;
const TTL_S = 60 * 60 * 24 * 400;

// v3890 (#182, his 11-09 "they need to separate like they were") - the OLD ALT is its own profile, under the name its
// Fleet row already carries; it no longer joins Konyo · ALT's ring (each PC is its own profile)
export const OWNERS = ["Konyo · Mac", "Konyo · ALT", "Konyo · GrokBot", "Dean", "Wife PC", "OLD PC ALT"];
const SECTIONS = ["characters", "vault", "stash", "owned", "chronicle", "reels"];

const QUOTA_WHY = "roster would not take this publish: quota";
const REFUSAL_HINT = "this is the storage refusing a write, NOT the machine being absent";
const MAX_BODY = 80000;
const KEY_PREFIX = "rosterkey:";
/* v3862 (item 11) - APPROVE A NEW PC. A PC whose label already has another PC's key was refused for good until Konyo
   ran wrangler on the Mac by hand (the header above) - on 2026-11-04 the new work ALT sat refused as "Konyo · ALT"
   while the old ALT held the key. Now a refused publish whose signature VERIFIES under a different key leaves a pending
   request (one write per new key, 14 days), and a PC whose label is in APPROVERS signs {kind:"approve"} with ITS OWN
   registered key to put the new key in place (or deny it). No Cloudflare credential, no wrangler: the approval is
   checked like every other signed record here. */
const REQ_PREFIX = "rosterkeyreq:";
const REQ_TTL_S = 14 * 86400;
export const APPROVERS = ["Konyo · Mac"];
const APPROVE_SKEW_MS = 15 * 60 * 1000;
const SIGNATURE_HINT = "nothing was stored: the key registered for this owner did not sign this publish. " +
  "A PC that lost its key stays refused until Konyo resets the owner's key from the Mac; a key never changes by itself";

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function refuse(why) {
  return json({ ok: false, why: why, hint: REFUSAL_HINT }, 200);
}

function dayOf(ms) {
  return new Date(ms).toISOString().slice(0, 10);
}

export function hashOf(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0).toString(16);
}

export function stable(v) {
  if (v === null || typeof v !== "object") return JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(stable).join(",") + "]";
  const keys = Object.keys(v).sort();
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + stable(v[k])).join(",") + "}";
}

function dirtyString(s) {
  const low = String(s).toLowerCase();
  if (low.indexOf("data:image") !== -1 || low.indexOf("base64,") !== -1) return true;
  if (/\.(jpg|jpeg|png|gif|webp)(\b|$)/i.test(s)) return true;
  if (s.length > 400) return true;
  return false;
}

function dirty(v) {
  if (typeof v === "string") return dirtyString(v);
  if (Array.isArray(v)) return v.some(dirty);
  if (v && typeof v === "object") {
    return Object.keys(v).some((k) => dirtyString(k) || dirty(v[k]));
  }
  return false;
}

export function shapeSection(raw) {   // exported for its law (REG-2745)
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const asOf = raw.asOf;
  if (typeof asOf !== "number" || !Number.isFinite(asOf) || asOf <= 0) return null;
  const out = { asOf: asOf };
  if (typeof raw.counts === "number" && Number.isFinite(raw.counts) && raw.counts >= 0) {
    out.counts = raw.counts;
  } else if (raw.counts && typeof raw.counts === "object" && !Array.isArray(raw.counts)) {
    const counts = {};
    for (const k of Object.keys(raw.counts)) {
      const v = raw.counts[k];
      if (dirtyString(k)) continue;
      if (typeof v === "number" && Number.isFinite(v) && v >= 0) counts[k] = v;
      else if (v && typeof v === "object" && !Array.isArray(v)) {
        const pair = {};
        if (typeof v.have === "number" && v.have >= 0) pair.have = v.have;
        if (typeof v.total === "number" && v.total > 0) pair.total = v.total;
        if (Object.keys(pair).length) counts[k] = pair;
      }
    }
    if (Object.keys(counts).length) out.counts = counts;
  }
  if (Array.isArray(raw.rows) && raw.rows.length) out.rows = raw.rows;
  if (!("counts" in out) && !("rows" in out)) return null;
  // #200 (REG-2745) - when the rows were read; kept beside them, never hashed (forHash below)
  if (out.rows && typeof raw.rowsAsOf === "number" && Number.isFinite(raw.rowsAsOf) && raw.rowsAsOf > 0) out.rowsAsOf = raw.rowsAsOf;
  // v3866 (his call 2026-11-06) - the vault's sweep evidence beside the board's records: a count and that store's own age
  const sw = raw.sweep;
  if (sw && typeof sw === "object" && !Array.isArray(sw) && Number.isInteger(sw.owned) && sw.owned >= 0
      && typeof sw.asOf === "number" && Number.isFinite(sw.asOf) && sw.asOf > 0) out.sweep = { owned: sw.owned, asOf: sw.asOf };
  return out;
}

export function forHash(sections) {   // exported for its law (REG-2745)
  const o = {};
  for (const name of Object.keys(sections).sort()) {
    const sec = sections[name];
    const c = {};
    for (const k of Object.keys(sec).sort()) {
      if (k === "asOf" || k === "rowsAsOf" || k === "hash") continue;   // REG-2745
      c[k] = (k === "sweep" && sec[k] && typeof sec[k] === "object") ? { owned: sec[k].owned } : sec[k];   // v3866 - its count only
    }
    o[name] = c;
  }
  return hashOf(stable(o));
}

function priorSections(prev) {
  const out = {};
  const s = prev && prev.sections;
  if (!s || typeof s !== "object" || Array.isArray(s)) return out;
  for (const name of SECTIONS) {
    const sec = s[name];
    if (!sec || typeof sec !== "object" || Array.isArray(sec)) continue;
    const copy = {};
    for (const k of Object.keys(sec)) {
      if (k === "rows" && Array.isArray(sec[k]) && sec[k].length === 0) continue;
      copy[k] = sec[k];
    }
    if (Object.keys(copy).length) out[name] = copy;
  }
  return out;
}

function bytesOfB64u(text) {
  if (typeof text !== "string") return null;
  const t = text.trim().replace(/=+$/, "");
  if (!t || !/^[A-Za-z0-9_-]+$/.test(t) || t.length % 4 === 1) return null;
  let bin = "";
  try { bin = atob(t.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((t.length + 3) % 4)); } catch (e) {
    return null;
  }
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function b64uOfBytes(bytes) {
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

// The short public name of a key: the first 12 hex of SHA-256 over its 32 raw bytes.
// tv/roster_sign.py key_id() computes the same, so a PC can compare its own key with a row's.
async function keyIdOf(pub) {
  const d = new Uint8Array(await crypto.subtle.digest("SHA-256", pub));
  let hex = "";
  for (let i = 0; i < 6; i++) hex += (d[i] < 16 ? "0" : "") + d[i].toString(16);
  return hex;
}

// #95 - what the two headers prove about these exact bytes. -> {state: none | valid | bad, ...}
export async function signatureOf(request, bytes) {
  const keyText = request.headers.get("x-roster-key");
  const sigText = request.headers.get("x-roster-sig");
  if (!keyText && !sigText) return { state: "none" };
  if (!keyText || !sigText) return { state: "bad", why: "one signature header came without the other" };
  const pub = bytesOfB64u(keyText);
  const sig = bytesOfB64u(sigText);
  if (!pub || pub.length !== 32) return { state: "bad", why: "the public key is not 32 bytes of base64url" };
  if (!sig || sig.length !== 64) return { state: "bad", why: "the signature is not 64 bytes of base64url" };
  const keyId = await keyIdOf(pub);
  let ok = false;
  try {
    const verifier = await crypto.subtle.importKey("raw", pub, { name: "Ed25519" }, false, ["verify"]);
    ok = await crypto.subtle.verify({ name: "Ed25519" }, verifier, sig, bytes);
  } catch (e) {
    return { state: "bad", keyId: keyId, why: "the signature could not be checked: " + String((e && e.name) || e).slice(0, 60) };
  }
  if (ok !== true) return { state: "bad", keyId: keyId, why: "the signature does not match these bytes" };
  return { state: "valid", pub: b64uOfBytes(pub), keyId: keyId };
}

// #95 - may this owner's row be written by this publish, and is it the owner's intent?
// -> {refused: why, registeredKeyId} | {verified, keyId, register}
// v3880 (#27) - ONE LABEL, MORE THAN ONE PC. His 11-05 ruling for the two ALTs: "share the profile, just split the rows".
// The registered record keeps its first key ({pub, keyId}) and may hold RING_MAX more in `also` - each another PC he
// approved for the label with "add" (approvePost), never one that replaced the first. Each such PC publishes into its own
// slot: the rows, the profile and the frames digest are stored under the record's name + "@" + its key id, so two PCs of one
// label never overwrite each other. A slot is a 12-hex key id; anything else in `also` is skipped, never trusted.
export const RING_MAX = 2;
export function ringOf(registered) {
  const also = registered && typeof registered === "object" && Array.isArray(registered.also) ? registered.also : [];
  const out = [];
  for (const e of also) {
    if (!e || typeof e !== "object" || typeof e.keyId !== "string" || !/^[0-9a-f]{12}$/.test(e.keyId)) continue;
    const pub = bytesOfB64u(e.pub);
    if (!pub || pub.length !== 32) continue;
    if (out.some((o) => o.slot === e.keyId)) continue;
    out.push({ slot: e.keyId, pub: b64uOfBytes(pub) });
    if (out.length >= RING_MAX) break;
  }
  return out;
}
// -> the slot (key id) of the ring key that `pub` is, or null
export function ringSlotOf(registered, pub) {
  if (typeof pub !== "string" || !pub) return null;
  const hit = ringOf(registered).find((e) => e.pub === pub);
  return hit ? hit.slot : null;
}
export function slotName(base, slot) {
  return slot ? base + "@" + slot : base;
}

export function intentOf(owner, registered, sig) {
  if (registered !== null) {
    const regPub = registered && typeof registered === "object" ? bytesOfB64u(registered.pub) : null;
    if (!regPub || regPub.length !== 32) {
      return { refused: "the key registered for " + owner + " is unreadable (not 32 bytes of base64url)" };
    }
    const regId = typeof registered.keyId === "string" ? registered.keyId.slice(0, 16) : null;
    if (sig.state === "none") {
      return { refused: owner + " has a registered key and this publish was not signed", registeredKeyId: regId };
    }
    if (sig.state !== "valid") {
      return { refused: "the signature did not verify (" + sig.why + ")", registeredKeyId: regId };
    }
    if (sig.pub !== b64uOfBytes(regPub)) {
      // v3880 (#27, his 11-05 ruling "share the profile, just split the rows") - another PC he approved for this label
      // signs with its own key; it publishes into its own slot (the record name + "@" + its key id), never over the first
      const slot = ringSlotOf(registered, sig.pub);
      if (slot) return { verified: true, keyId: sig.keyId, register: false, slot: slot };
      return { refused: "this publish was signed by a different key than the one registered for " + owner, registeredKeyId: regId };
    }
    return { verified: true, keyId: sig.keyId, register: false };
  }
  if (sig.state === "valid") return { verified: true, keyId: sig.keyId, register: true };
  return { verified: false, keyId: null, register: false };
}

function refuseSignature(intent, sig, requested) {
  const out = { ok: false, why: "roster would not take this publish: " + intent.refused, hint: SIGNATURE_HINT, sig: sig.state };
  if (intent.registeredKeyId) out.keyId = intent.registeredKeyId;
  if (sig.keyId) out.offered = sig.keyId;
  if (requested) {
    out.approval = "requested";
    out.why += " - this PC's key (" + sig.keyId + ") is waiting for " + APPROVERS.join(" or ") + " to approve it";
  }
  return json(out, 200);
}

// v3862 (item 11) - a valid signature under ANOTHER key than the registered one: remember it as a request to approve.
// -> true when a request for this exact key is pending (written now or already there). Never throws.
export async function noteKeyRequest(kv, owner, sig, registeredKeyId, now) {
  if (!sig || sig.state !== "valid" || !sig.pub || !sig.keyId) return false;
  const name = REQ_PREFIX + owner;
  try {
    const raw = await kv.get(name);
    const prev = raw ? JSON.parse(raw) : null;
    if (prev && prev.pub === sig.pub) return true;          // the same key asking again costs no write
    await kv.put(name, JSON.stringify({ owner: owner, pub: sig.pub, keyId: sig.keyId, at: now,
                                        replaces: registeredKeyId || null }), { expirationTtl: REQ_TTL_S });
    return true;
  } catch (e) {
    return false;
  }
}

// v3890 (#182) - take keyId out of the ring of every label but `owner`. -> [the labels it left]
export async function leaveOtherRings(kv, owner, keyId) {
  const left = [];
  for (const other of OWNERS) {
    if (other === owner) continue;
    let rec = null;
    try { rec = await registeredOf(kv, other); } catch (e) { rec = null; }
    if (!rec || !Array.isArray(rec.also) || !rec.also.some((e) => e && e.keyId === keyId)) continue;
    const kept = rec.also.filter((e) => !(e && e.keyId === keyId));
    const next = Object.assign({}, rec);
    if (kept.length) next.also = kept; else delete next.also;
    await kv.put(KEY_PREFIX + other, JSON.stringify(next));
    left.push(other);
  }
  return left;
}

// v3862 (item 11) - {kind:"approve", approver, owner, keyId, decision:"approve"|"deny", signedAt}, signed by the
// approver's REGISTERED key. -> the Response
export async function approvePost(env, sig, body) {
  const kv = env && env.TZ_HISTORY;
  if (!kv) return refuse("roster would not take this approval: storage unavailable");
  const approver = body.approver, owner = body.owner, decision = body.decision;
  if (APPROVERS.indexOf(approver) === -1) return refuse("roster would not take this approval: " + String(approver).slice(0, 40) + " may not approve a PC");
  if (OWNERS.indexOf(owner) === -1) return refuse("roster would not take this approval: the owner is not one of the owner labels");
  if (decision !== "approve" && decision !== "deny" && decision !== "add") {
    return refuse("roster would not take this approval: decision is approve, add or deny");
  }
  // v3890 (#182, his 11-09: "thats not good that its mixed ... each console and whatever it itself is rendering should be
  // showing ... at that individual profile") - EACH PC IS ITS OWN PROFILE. "Add as another PC" joined the OLD ALT to Konyo ·
  // ALT and his shadow of that profile showed the OLD ALT's 26 characters as the work ALT's. A PC now gets a profile of its
  // own: approve it under its own label.
  if (decision === "add") {
    return refuse("roster would not take this approval: each PC is its own profile now - approve it under its own label");
  }
  const now = Date.now();
  if (typeof body.signedAt !== "number" || !Number.isFinite(body.signedAt) || Math.abs(now - body.signedAt) > APPROVE_SKEW_MS) {
    return refuse("roster would not take this approval: signedAt is missing or not within 15 min of now");
  }
  let registered;
  try { registered = await registeredOf(kv, approver); } catch (e) { registered = undefined; }
  if (!registered) return refuse("roster would not take this approval: " + approver + " has no registered key");
  const intent = intentOf(approver, registered, sig);
  if (intent.refused || intent.verified !== true || intent.register) {
    return refuse("roster would not take this approval: " + (intent.refused || "it was not signed by " + approver + "'s registered key"));
  }
  const name = REQ_PREFIX + owner;
  let req = null;
  try { const raw = await kv.get(name); req = raw ? JSON.parse(raw) : null; } catch (e) { req = null; }
  if (!req || typeof req !== "object" || req.keyId !== body.keyId || !req.pub) {
    return refuse("roster would not take this approval: no pending request from key " + String(body.keyId).slice(0, 16) + " for " + owner);
  }
  // v3880 (#27) - the owner's record as it stands, so an approval never drops another PC he approved for this label
  let held = null;
  try { held = await registeredOf(kv, owner); } catch (e) {
    return refuse("roster would not take this approval: the key registered for " + owner + " could not be read");
  }
  const ring = held ? (Array.isArray(held.also) ? held.also.filter((e) => e && typeof e === "object") : []) : [];
  if (decision === "approve") {
    const rec = { pub: req.pub, keyId: req.keyId, at: now, approvedBy: approver, replaced: req.replaces || null };
    const kept = ring.filter((e) => e.keyId !== req.keyId);
    if (kept.length) rec.also = kept;
    await kv.put(KEY_PREFIX + owner, JSON.stringify(rec));
    // v3890 (#182) - ONE KEY, ONE PROFILE: a PC approved under its own label leaves every other label's ring, so the profile
    // it used to share stops serving its characters and rows as that profile's
    await leaveOtherRings(kv, owner, req.keyId);
  } else if (decision === "add") {
    // "ANOTHER PC OF THIS LABEL" - the first key stays; the new one joins the ring, its rows and profile kept apart
    if (!held || !held.pub) return refuse("roster would not take this approval: " + owner + " has no first key to add a PC beside");
    if (ring.some((e) => e.keyId === req.keyId)) {
      await kv.delete(name);
      return json({ ok: true, owner: owner, keyId: req.keyId, decision: decision, by: approver, already: true }, 200);
    }
    if (ringOf(held).length >= RING_MAX) {
      return refuse("roster would not take this approval: " + owner + " already holds " + RING_MAX + " other PCs - deny or replace one");
    }
    const rec = Object.assign({}, held, { also: ring.concat([{ pub: req.pub, keyId: req.keyId, at: now, approvedBy: approver }]) });
    await kv.put(KEY_PREFIX + owner, JSON.stringify(rec));
  }
  await kv.delete(name);
  return json({ ok: true, owner: owner, keyId: req.keyId, decision: decision, by: approver }, 200);
}

// v3864 (his ask 2026-11-05, card 57) - THE TASK BOARD ONLINE. {kind:"tasks", poster, board:{title, at, counts, cards}, signedAt},
// signed by an APPROVER's registered key (his Mac publishes its board; no other PC may), the board scrubbed on the Mac before
// it was signed (tv/task_board.py). One KV record, replaced; a write closer than TASKS_MIN_GAP_MS to the last is refused, so a
// busy board cannot spend the KV budget. GET ?tasks=1 hands it to /d2r/tasks.html (behind the site password).
export const TASKS_KEY = "tasks:board";
export const TASKS_MAX_BODY = 200000;
export const TASKS_MIN_GAP_MS = 60 * 1000;
export async function tasksPost(env, bytes, sig, body) {
  const kv = env && env.TZ_HISTORY;
  if (!kv) return refuse("roster would not take this board: storage unavailable");
  if (!bytes || bytes.byteLength > TASKS_MAX_BODY) return refuse("roster would not take this board: it is larger than the board it keeps");
  const poster = body.poster;
  if (APPROVERS.indexOf(poster) === -1) return refuse("roster would not take this board: " + String(poster).slice(0, 40) + " does not publish the board");
  const now = Date.now();
  if (typeof body.signedAt !== "number" || !Number.isFinite(body.signedAt) || Math.abs(now - body.signedAt) > APPROVE_SKEW_MS) {
    return refuse("roster would not take this board: signedAt is missing or not within 15 min of now");
  }
  const b = body.board;
  if (!b || typeof b !== "object" || !Array.isArray(b.cards) || b.cards.length > 400) {
    return refuse("roster would not take this board: it has no list of cards");
  }
  let registered;
  try { registered = await registeredOf(kv, poster); } catch (e) { registered = undefined; }
  if (!registered) return refuse("roster would not take this board: " + poster + " has no registered key");
  const intent = intentOf(poster, registered, sig);
  if (intent.refused || intent.verified !== true || intent.register) {
    return refuse("roster would not take this board: " + (intent.refused || "it was not signed by " + poster + "'s registered key"));
  }
  let prev = null;
  try { const raw = await kv.get(TASKS_KEY); prev = raw ? JSON.parse(raw) : null; } catch (e) { prev = null; }
  if (prev && typeof prev.at === "number" && now - prev.at < TASKS_MIN_GAP_MS) {
    return refuse("roster would not take this board: the last one landed under a minute ago");
  }
  const keep = { at: now, by: poster, board: b };
  await kv.put(TASKS_KEY, JSON.stringify(keep));
  return json({ ok: true, at: now, cards: b.cards.length }, 200);
}

export async function tasksGet(kv) {
  if (!kv) return refuse("roster would not take this fetch: storage unavailable");
  let rec = null;
  try { const raw = await kv.get(TASKS_KEY); rec = raw ? JSON.parse(raw) : null; } catch (e) { rec = null; }
  if (!rec || typeof rec !== "object" || !rec.board) return json({ ok: true, board: null, why: "his Mac has not published the board yet" }, 200);
  return json({ ok: true, at: rec.at, by: rec.by, board: rec.board }, 200);
}

// v3862 (item 11) - the pending requests, for an approver's fleet card. Key ids and times only; never a pub key.
export async function requestsGet(kv) {
  if (!kv) return refuse("roster would not take this fetch: storage unavailable");
  const out = [];
  for (const owner of OWNERS) {
    let req = null;
    try { const raw = await kv.get(REQ_PREFIX + owner); req = raw ? JSON.parse(raw) : null; } catch (e) { req = null; }
    if (req && typeof req === "object" && typeof req.keyId === "string") {
      out.push({ owner: owner, keyId: req.keyId.slice(0, 16), at: typeof req.at === "number" ? req.at : null,
                 replaces: typeof req.replaces === "string" ? req.replaces.slice(0, 16) : null });
    }
  }
  return json({ ok: true, requests: out, approvers: APPROVERS }, 200);
}

export async function onRequestPost(context) {
  const { request, env } = context;
  const kv = env && env.TZ_HISTORY;
  if (!kv) return refuse("roster would not take this publish: storage unavailable");

  let bytes = new Uint8Array(0);
  try { bytes = new Uint8Array(await request.arrayBuffer()); } catch (e) { bytes = new Uint8Array(0); }
  // REG-2794 (the v3829 second eye) - the door's first cap is the LARGEST any kind may send. It was the profile's 200 KB, so
  // a frames digest (its own cap, built up of film-size frames) past 200 KB was refused as "too large to be
  // rows" before it reached its own door. Each kind still enforces its own cap: rows MAX_BODY, profile PROFILE_MAX_BODY,
  // frames FRAMES_MAX_BODY.
  if (bytes.byteLength > FRAMES_MAX_BODY) {
    return refuse("roster would not take this publish: the body is larger than any record it keeps");
  }
  // #95 - the signature is checked over the bytes as they arrived, before JSON.parse and before any write.
  const sig = await signatureOf(request, bytes);
  let text = "";
  try { text = new TextDecoder("utf-8").decode(bytes); } catch (e) { text = ""; }
  let body;
  try { body = JSON.parse(text || "{}"); } catch (e) {
    return refuse("roster would not take this publish: the body was not JSON");
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return refuse("roster would not take this publish: the body was not a record");
  }
  // Shadow mode's profile rides this same route under its own key; rows keep their own 80 KB cap.
  if (body.kind === "approve") return approvePost(env, sig, body);   // v3862 (item 11)
  if (body.kind === "tasks") return tasksPost(env, bytes, sig, body);  // v3864 (card 57) his Mac's board
  if (body.kind === "profile") return profilePost(env, bytes, sig, body);
  // #218 phase 2 - the owner's sessions, summarized (shadow_sessions.digest), under the same registered key
  if (body.kind === "frames") return framesPost(env, bytes, sig, body);
  if (bytes.byteLength > MAX_BODY) {
    return refuse("roster would not take this publish: the body is too large to be rows");
  }

  const owner = body.owner;
  if (OWNERS.indexOf(owner) === -1) {
    return refuse("roster would not take this publish: the key is an owner label, not a machine");
  }
  if (dirty(body)) {
    return refuse("roster would not take this publish: pictures stay on that PC");
  }

  const shaped = {};
  const incoming = (body.sections && typeof body.sections === "object") ? body.sections : {};
  for (const name of SECTIONS) {
    if (!Object.prototype.hasOwnProperty.call(incoming, name)) continue;
    const sec = shapeSection(incoming[name]);
    if (sec) shaped[name] = sec;
  }

  const key = "roster:" + owner;
  const keyName = KEY_PREFIX + owner;
  let held = null;
  try { held = await kv.get(keyName); } catch (e) {
    return refuse("roster would not take this publish: the key registered for this owner could not be read");
  }
  // A key Konyo put there by hand may be the bare base64url string rather than the record this file writes.
  // Anything else stored under the name still counts as a registered key, unreadable: it fails closed.
  let registered = null;
  if (held) {
    try { registered = JSON.parse(held); } catch (e) { registered = { pub: String(held).trim() }; }
    if (typeof registered === "string") registered = { pub: registered };
    if (!registered || typeof registered !== "object") registered = { pub: null };
  }
  const intent = intentOf(owner, registered, sig);
  if (intent.refused) {
    // v3862 (item 11) - a valid signature under another key is a new PC asking for this label: remember it for approval
    // only a READABLE registered key can be replaced by an approval - an unreadable one stays a refusal and writes nothing
    // REG-3265 (the Grok CLI on REG-3163, #231 6681926045) - a key placed by hand is often the bare pub with no keyId (the
    // shape this file still accepts). It is READABLE - 32 bytes - so its id is derived the way every id is (keyIdOf);
    // without it the request was never written and the refusal never said a key was waiting. An unreadable one has no
    // 32 bytes to hash and still writes nothing.
    let regKeyId = intent.registeredKeyId || null;
    if (!regKeyId && registered && sig.state === "valid") {
      const rp = bytesOfB64u(registered.pub);
      if (rp && rp.length === 32) {
        try { regKeyId = await keyIdOf(rp); } catch (e) { regKeyId = null; }
      }
    }
    const asked = (registered && regKeyId && sig.state === "valid")
      ? await noteKeyRequest(kv, owner, sig, regKeyId, Date.now()) : false;
    return refuseSignature(intent, sig, asked);
  }

  const rowKey = slotName(key, intent.slot);          // v3880 (#27) - another PC of this label keeps its own rows
  let prev = null;
  try {
    const raw = await kv.get(rowKey);
    prev = raw ? JSON.parse(raw) : null;
  } catch (e) { prev = null; }
  if (!prev || typeof prev !== "object" || prev.owner !== owner) prev = null;

  const now = Date.now();
  const boot = body.boot === true;
  const verified = intent.verified === true;
  const keyId = verified ? intent.keyId : null;
  // The whole public key a verified row was written under. keyId is 48 bits of it, a name for people to
  // compare; two keys can share one, so "the same key" is asked of the key itself.
  const pub = verified ? sig.pub : null;
  const prevPub = prev && prev.intentVerified === true && typeof prev.pub === "string" ? prev.pub : null;
  const sameIntent = !!prev && prev.intentVerified === verified && prevPub === pub && (prev.keyId || null) === keyId;
  // REG-2516 - a verified row holds only what its own key signed. A section is carried over from the stored
  // row only when that row was written under this very key. Merging every prior section into a signed write
  // stamped rows this key never signed - planted unsigned before the key was registered, written before
  // signing, or another key's - "signature verified (key ...)" for good, because a PC never re-sends a section
  // it does not read (no PC sends `owned`). An unsigned write still merges: it is stored NOT verified, and says so.
  const inherit = !verified || sameIntent;
  const sections = Object.assign(inherit ? priorSections(prev) : {}, shaped);
  const hash = forHash(sections);
  // What this publish's signature proved, said on every answer so the PC can record it.
  const said = { intentVerified: verified, sig: sig.state };
  if (keyId) said.keyId = keyId;
  if (sig.state === "bad") said.sigWhy = sig.why;
  // A row that becomes verified, changes key, or registers its key is written even when unchanged
  // and inside the hour: that is the owner's key arriving, not a churn of rows. The daily cap holds.
  const upgrade = verified && (!sameIntent || intent.register === true);

  if (!Object.keys(sections).length) {
    return json(Object.assign({ ok: true, owner: owner, stored: [], skipped: ["nothing read"] }, said), 200);
  }
  if (prev && prev.hash === hash && sameIntent && !upgrade) {
    return json(Object.assign({ ok: true, owner: owner, stored: [], skipped: ["unchanged"] }, said), 200);
  }
  const age = prev && typeof prev.t === "number" ? (now - prev.t) : HOUR_MS;
  if (prev && age < HOUR_MS && !boot && !upgrade) {
    return json(Object.assign({ ok: true, owner: owner, stored: [], skipped: ["within the hour"] }, said), 200);
  }

  const today = dayOf(now);
  const n = (prev && prev.day === today && typeof prev.n === "number") ? prev.n : 0;
  if (n >= ROSTER_CAP) {
    return json({ ok: false, why: QUOTA_WHY, hint: REFUSAL_HINT }, 200);
  }

  if (intent.register) {
    try {
      await kv.put(keyName, JSON.stringify({ pub: sig.pub, keyId: sig.keyId, at: now }));
    } catch (e) {
      return refuse("roster would not take this publish: " + String((e && e.message) || e).slice(0, 140));
    }
    said.registered = true;
    // v3890 (#182) - ONE KEY, ONE PROFILE: a PC registering its own label leaves every other label's ring (the OLD ALT,
    // first publishing as OLD PC ALT, leaves Konyo · ALT) - so that profile stops serving its rows and characters
    try {
      const left = await leaveOtherRings(kv, owner, sig.keyId);
      if (left.length) said.leftRings = left;
    } catch (e) {
      said.leftRingsWhy = "could not leave the other profiles' rings: " + String((e && e.message) || e).slice(0, 80);
    }
  }
  const rec = { owner: owner, t: now, day: today, n: n + 1, hash: hash, sections: sections };
  rec.intentVerified = verified;
  if (keyId) rec.keyId = keyId;
  if (pub) rec.pub = pub;
  if (verified && typeof body.signedAt === "number" && Number.isFinite(body.signedAt)) rec.signedAt = body.signedAt;
  if (intent.slot) { rec.slot = intent.slot; said.slot = intent.slot; }
  try {
    await kv.put(rowKey, JSON.stringify(rec), { expirationTtl: TTL_S });
  } catch (e) {
    return refuse("roster would not take this publish: " + String((e && e.message) || e).slice(0, 140));
  }
  return json(Object.assign({ ok: true, owner: owner, stored: ["roster"], key: rowKey }, said), 200);
}

// v3880 (#27) - "split the rows": the rows each OTHER PC of this label published into its own slot, while its key is in
// the ring and its sections still match their hash. -> [{keyId, t, sections}]
async function otherRowsOf(kv, owner) {
  let registered = null;
  try { registered = await registeredOf(kv, owner); } catch (e) { return []; }
  const out = [];
  for (const e of ringOf(registered)) {
    let rec = null;
    try { const raw = await kv.get(slotName("roster:" + owner, e.slot)); rec = raw ? JSON.parse(raw) : null; } catch (x) { rec = null; }
    if (!rec || typeof rec !== "object" || rec.owner !== owner || rec.slot !== e.slot) continue;
    if (rec.intentVerified !== true || b64uKey(rec.pub) !== b64uKey(e.pub)) continue;
    const sections = priorSections(rec);
    if (rec.hash !== forHash(sections)) continue;
    out.push({ keyId: e.slot, t: rec.t, sections: sections });
  }
  return out;
}

export async function onRequestGet(context) {
  const kv = context.env && context.env.TZ_HISTORY;
  let profileOwner = null;
  try { profileOwner = new URL(context.request.url).searchParams.get("profile"); } catch (e) { profileOwner = null; }
  if (profileOwner !== null) return profileGet(kv, profileOwner);
  let framesOwner = null;
  try { framesOwner = new URL(context.request.url).searchParams.get("frames"); } catch (e) { framesOwner = null; }
  if (framesOwner !== null) return framesGet(kv, framesOwner);
  let wantRequests = null;
  try { wantRequests = new URL(context.request.url).searchParams.get("requests"); } catch (e) { wantRequests = null; }
  if (wantRequests !== null) return requestsGet(kv);   // v3862 (item 11)
  let wantTasks = null;
  try { wantTasks = new URL(context.request.url).searchParams.get("tasks"); } catch (e) { wantTasks = null; }
  if (wantTasks !== null) return tasksGet(kv);         // v3864 (card 57)
  if (!kv) return refuse("roster would not take this fetch: storage unavailable");
  const owners = [];
  for (const owner of OWNERS) {
    let raw = null;
    try {
      raw = await kv.get("roster:" + owner);
    } catch (e) {
      return refuse("roster would not take this fetch: " + String((e && e.message) || e).slice(0, 140));
    }
    let prev = null;
    try { prev = raw ? JSON.parse(raw) : null; } catch (e) { prev = null; }
    if (!prev || typeof prev !== "object" || prev.owner !== owner) {
      owners.push({ owner: owner, published: false });
      continue;
    }
    const sections = priorSections(prev);
    const hash = forHash(sections);
    if (prev.hash !== hash) {
      owners.push({ owner: owner, published: true, corrupt: true, t: prev.t });
      continue;
    }
    const row = { owner: owner, published: true, corrupt: false, t: prev.t, hash: hash };
    // #95 - passed only when the record holds a boolean: a row stored before signing has none,
    // and a viewer must show it UNKNOWN, never verified and never unverified.
    if (typeof prev.intentVerified === "boolean") row.intentVerified = prev.intentVerified;
    if (typeof prev.keyId === "string" && /^[0-9a-f]{12}$/.test(prev.keyId)) row.keyId = prev.keyId;
    if (typeof prev.signedAt === "number" && Number.isFinite(prev.signedAt)) row.signedAt = prev.signedAt;
    if (Object.keys(sections).length) row.sections = sections;
    const others = await otherRowsOf(kv, owner);
    if (others.length) row.others = others;
    owners.push(row);
  }
  return json({ ok: true, owners: owners }, 200);
}

// ── PROFILE: this owner's whole account stores, for shadow mode (one to one, read only) ──────────────
// Elad 2026-10-24: shadow syncs on the SAME path Fleet and the Roster use, saved under that PC's own profile,
// with no separate upload. The console's roster publish lane sends {kind:"profile", owner, boot, signedAt, hash,
// stores} to this route signed with the key the roster rows registered; GET /api/roster?profile=<owner> reads it.
export function profileKeyOf(owner) {
  return "roster:" + owner + ":profile";
}

const PROFILE_MAX_BODY = 200000;
const PROFILE_DAY_CAP = 150;                    // v3862 paid: the console posts at most every 10 min (was 20 a day)
const PROFILE_MIN_GAP_MS = 8 * 60 * 1000;       // the worker refuses only inside 8 min (the console waits 10)
const STORE_NAME = /^d2r_[A-Za-z0-9_]{1,60}$/;
// A signed body is fresh for this long either side of the worker's clock, and each one must be newer than the last
// stored: a captured upload (the boot one skips the gap) cannot be replayed to roll a console back.
const SKEW_MS = 15 * 60 * 1000;
// The same stores tv/console_snapshot.py keeps home (DENY, DENY_PREFIX, API_FIELDS - a law holds them equal): a
// signed client that skipped the console's cleaning still cannot park identity, history or debug stores here.
export const DENY = [
  "d2r_tvdHist", "d2r_tvdTallyLog", "d2r_chronicleInboxLog", "d2r_foundEvidence", "d2r_sessionLog",
  "d2r_intakeLog", "d2r_intakeSeen", "d2r_intakeUrl", "d2r_lsrRoute", "d2r_tz_hist_cache",
  "d2r_unseedBackup", "d2r_unseedReport", "d2r_unseedRestoreReport", "d2r_vaultLastReset",
  "d2r_createNow", "d2r_createNowDate", "d2r_createNowAi", "d2r_createNowAiArt", "d2r_createNowAiV",
  "d2r_createNowAiDate", "d2r_aicDraft", "d2r_aicQueue", "d2r_aicThrownLog", "d2r_lastTopScan",
  "d2r_grailFarm", "d2r_storeEmptied", "d2r_installId", "d2r_installIdCache", "d2r_ownerClaim",
  "d2r_activeProfile", "d2r_activeProfileWin", "d2r_activeMachine", "d2r_machineSource",
  "d2r_inboxReader", "d2r_logger", "d2r_testGuest",
];
export const DENY_PREFIX = ["d2r_quarantine", "d2r_d2jsp_", "d2r_api_"];
export const API_NAMES = ["chars_learned", "main_locks", "world", "pictures", "saves", "d2jsp_login"];
// the fields each console answer may carry (console_snapshot.API_FIELDS) and the world's closed values (world_of)
export const API_FIELDS = {
  // REG-3080 - sessions/sessionsWhy (REG-2907) were added on the console side only, and apiOk refuses a field outside this
  // list, so EVERY profile carrying the characters answer was refused whole ("d2r_api_chars_learned is not the console
  // answer it names") from the v3837 console on: shadows froze on their last profile. A law now holds each name's FIELDS equal.
  chars_learned: ["ok", "chars", "gear", "gearWhy", "minVisits", "tierBars", "cPanel", "surfaceWitnesses", "lobbyBySize",
                  "sessions", "sessionsWhy", "identity"],   // v3856 - read_identity rides chars_learned (finds_index, characters_rollup)
  main_locks: ["ok", "locked", "tracked", "floor", "minSightings", "canEverLock", "blockedWhy"],
  world: ["machine", "profile", "ledger", "os", "cousin"],
  // v3849 - a shadow draws the owner's frame: the console's picture map (console_snapshot.pictures_of) rides the
  // profile, and a name missing here refused the whole profile exactly as REG-3080 did.
  pictures: ["ok", "pictures", "origin"],
  // #251 (REG-3079) - the owner's reason its saves name what they name; #104 - and their save NAMES (savesOk: names only)
  saves: ["ok", "state", "d2sWhy", "why", "chars"],
  // #45 (REG-3461) - the owner's d2jsp sign-in, three closed words (console_snapshot.d2jsp_login_of; d2jspLoginOk below)
  d2jsp_login: ["ok", "state", "kind"],
};
const WORLD = { machine: ["mac", "windows"], profile: ["main", "ladder"],
                os: ["MAC", "WINDOWS", "LINUX", "ANDROID", "THIS MACHINE"] };
// what console_snapshot._PRIVATE blanks: a signed body that still carries one was not cleaned, and is refused
const PRIVATE = [
  /(?:\/Users\/|\/home\/|\/private\/|\/var\/folders\/)/,
  /[A-Za-z]:\\{1,2}(?:Users|Documents and Settings)\\/,
  /(?<![0-9a-fA-F])[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}(?![0-9a-fA-F])/,
  /(?<![0-9a-fA-F])[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-fA-F])/,
  /\b(?:ghp_|gho_|ghs_|github_pat_|xox[abposr]-|sk-)[A-Za-z0-9_\-]{16,}/,
  /\b[A-Za-z0-9][A-Za-z0-9\-]{0,62}\.local\b/,
  /\bI?L?·[0-9a-f]{8}·/,
  /data:image\//,
];

export function privateIn(raw) {
  // the raw text as sent: a store that is not JSON, or a path or token written plainly
  if (PRIVATE.some((rx) => rx.test(raw))) return true;
  // every JSON string literal (keys too) decoded on its own: an escaped \/Users\/ or \u0067hp_ is read as itself,
  // including a value under a repeated key that JSON.parse would drop
  const lits = raw.match(/"(?:[^"\\]|\\.)*"/g) || [];
  for (const lit of lits) {
    let t;
    try { t = JSON.parse(lit); } catch (e) { continue; }
    if (PRIVATE.some((rx) => rx.test(t))) return true;
  }
  return false;
}

export function worldOk(text) {
  let w;
  try { w = JSON.parse(text); } catch (e) { return false; }
  if (!w || typeof w !== "object" || Array.isArray(w)) return false;
  if (Object.keys(w).some((k) => API_FIELDS.world.indexOf(k) === -1)) return false;
  for (const k of Object.keys(WORLD)) if (WORLD[k].indexOf(w[k]) === -1) return false;
  return typeof w.cousin === "boolean" && typeof w.ledger === "string" && w.ledger.length <= 40 &&
         !/[\x00-\x1f"<>\\]/.test(w.ledger);
}

// #104 - the saves answer's names ride a shadow, NAMES ONLY (console_snapshot.saves_of): each row {name} and nothing else,
// a D2R name (2-15 letters, at most one '-' or '_'), 40 at most - an id count or any other key is refused
const D2R_NAME = /^[A-Za-z][A-Za-z_-]{1,14}$/;
export function savesOk(text) {
  let v;
  try { v = JSON.parse(text); } catch (e) { return false; }
  if (!v || typeof v !== "object" || Array.isArray(v)) return false;
  if (Object.keys(v).some((k) => API_FIELDS.saves.indexOf(k) === -1)) return false;
  if (v.chars === undefined || v.chars === null) return true;
  if (!Array.isArray(v.chars) || v.chars.length > 40) return false;
  return v.chars.every((r) => r && typeof r === "object" && !Array.isArray(r) && Object.keys(r).length === 1 &&
    typeof r.name === "string" && D2R_NAME.test(r.name) && (r.name.match(/[-_]/g) || []).length <= 1);
}

// #45 (REG-3461) - the d2jsp sign-in answer is three closed words, nothing else: a sentence or a cookie never rides here
export function d2jspLoginOk(text) {
  let v;
  try { v = JSON.parse(text); } catch (e) { return false; }
  if (!v || typeof v !== "object" || Array.isArray(v)) return false;
  if (Object.keys(v).some((k) => API_FIELDS.d2jsp_login.indexOf(k) === -1)) return false;
  return v.ok === true && ["on", "off", "unknown"].indexOf(v.state) !== -1 &&
    ["on", "own-window", "signed-out", "signing-in", "unread"].indexOf(v.kind) !== -1;
}

export function apiOk(name, text) {   // exported for its law (REG-3080): the field check a profile store must pass
  if (name === "world") return worldOk(text);
  if (name === "saves") return savesOk(text);
  if (name === "d2jsp_login") return d2jspLoginOk(text);
  let v;
  try { v = JSON.parse(text); } catch (e) { return false; }
  if (!v || typeof v !== "object" || Array.isArray(v)) return false;
  return Object.keys(v).every((k) => API_FIELDS[name].indexOf(k) !== -1);
}
const PROFILE_HINT = "this is the storage refusing a write, NOT the machine being absent";

function pJson(obj) {
  return new Response(JSON.stringify(obj), {
    status: 200,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

function pRefuse(why, extra) {
  return pJson(Object.assign({ ok: false, why: "roster would not take this profile: " + why, hint: PROFILE_HINT }, extra || {}));
}

export function storesOk(stores) {
  if (!stores || typeof stores !== "object" || Array.isArray(stores)) return false;
  const names = Object.keys(stores);
  if (!names.length) return false;
  return names.every((k) => STORE_NAME.test(k) && typeof stores[k] === "string" && nameOk(k));
}

function nameOk(k) {
  if (k.startsWith("d2r_api_")) return API_NAMES.indexOf(k.slice(8)) !== -1;
  if (DENY.indexOf(k) !== -1) return false;
  return !DENY_PREFIX.some((p) => k.startsWith(p));
}

function b64uKey(v) {
  return typeof v === "string" ? v.trim().replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "") : null;
}

export function hashOfStores(stores) {
  return hashOf(stable(stores));
}

async function registeredOf(kv, owner) {
  const held = await kv.get(KEY_PREFIX + owner);
  if (!held) return null;
  let registered;
  try { registered = JSON.parse(held); } catch (e) { registered = { pub: String(held).trim() }; }
  if (typeof registered === "string") registered = { pub: registered };
  if (!registered || typeof registered !== "object") registered = { pub: null };
  return registered;
}

// The profile half of the one roster publish: same route, same registered key, its own KV record
// roster:<owner>:profile. roster's onRequestPost hands over the bytes it read and verified.
// #210 - a list of d2r_ store names (at most 40), or null when it is not one.
function unsentOf(v) {
  if (!Array.isArray(v) || v.length > 40) return null;
  for (const k of v) if (typeof k !== "string" || !/^d2r_[A-Za-z0-9_]{1,60}$/.test(k)) return null;
  return v.slice();
}

// #218 phase 2 - ONE gate for every signed record kind an owner publishes beside its roster row (the profile, the
// frames digest): the same registered key, the same intent, the same replay rule. Moved here VERBATIM from profilePost,
// so a second kind adds a caller, never a second copy of a safety routine. -> intent | a refusal Response
async function signedOwnerIntent(kv, owner, sig) {
  let registered;
  try { registered = await registeredOf(kv, owner); } catch (e) {
    return pRefuse("the key registered for this owner could not be read");
  }
  // A profile never registers a key: the roster publish is the one place trust is first given.
  if (registered === null) return pRefuse(owner + " has no registered roster key yet; a signed roster publish registers it");
  const intent = intentOf(owner, registered, sig);
  if (intent.refused || intent.verified !== true || intent.register) {
    const out = { sig: sig.state };
    if (intent.registeredKeyId) out.keyId = intent.registeredKeyId;
    if (sig.keyId) out.offered = sig.keyId;
    return pRefuse(intent.refused || "this upload was not signed by " + owner + "'s registered key", out);
  }
  return intent;
}

// -> a refusal Response when signedAt is missing, stale or not newer than the stored record's, else null
function signedAtRefusal(now, signedAt, prev) {
  if (typeof signedAt !== "number" || !Number.isFinite(signedAt) || Math.abs(now - signedAt) > SKEW_MS) {
    return pRefuse("signedAt is missing or not within 15 min of now (a replayed or stale upload)");
  }
  if (prev && typeof prev.signedAt === "number" && signedAt <= prev.signedAt) {
    return pRefuse("signedAt is not newer than the stored upload's (a replayed upload)");
  }
  return null;
}

// #218 phase 2 - ONE rule for every record served as an owner's (the profile, the frames digest): the key that signed
// it is that owner's registered key NOW. A record signed by a since-replaced key is not served as theirs.
function signedByRegisteredNow(registered, prev) {
  if (!registered || !registered.pub || b64uKey(registered.pub) !== b64uKey(prev.pub)) {
    return false;
  }
  return true;
}

async function profilePost(env, bytes, sig, body) {
  const kv = env && env.TZ_HISTORY;
  if (!kv) return pRefuse("storage unavailable");
  if (bytes.byteLength > PROFILE_MAX_BODY) return pRefuse("the body is larger than " + PROFILE_MAX_BODY + " bytes");
  const owner = body.owner;
  if (OWNERS.indexOf(owner) === -1) return pRefuse("the key is an owner label, not a machine");

  const intent = await signedOwnerIntent(kv, owner, sig);
  if (intent instanceof Response) return intent;

  const stores = body.stores;
  if (!storesOk(stores)) return pRefuse("stores must be d2r_ names holding strings, none of them kept home");
  const low = JSON.stringify(stores).toLowerCase();
  if (low.indexOf("data:image") !== -1 || low.indexOf("base64,") !== -1) return pRefuse("pictures stay on that PC");
  for (const k of Object.keys(stores)) {
    if (privateIn(stores[k])) return pRefuse(k + " carries a path, an install id or a token");
    if (k.startsWith("d2r_api_") && !apiOk(k.slice(8), stores[k])) return pRefuse(k + " is not the console answer it names");
  }
  if (typeof stores.d2r_api_world !== "string") return pRefuse("the world these stores were drawn in is missing");
  const hash = hashOfStores(stores);
  if (body.hash !== hash) return pRefuse("the stores do not match the hash that was signed");

  const key = slotName(profileKeyOf(owner), intent.slot);   // v3880 (#27) - another PC of this label: its own profile
  let prev = null;
  try {
    const raw = await kv.get(key);
    prev = raw ? JSON.parse(raw) : null;
  } catch (e) {
    // an unreadable record would skip the replay, gap and daily checks: refuse rather than start over
    return pRefuse("the stored profile could not be read");
  }
  if (!prev || typeof prev !== "object" || prev.owner !== owner) prev = null;

  const now = Date.now();
  const signedAt = body.signedAt;
  const stale = signedAtRefusal(now, signedAt, prev);
  if (stale) return stale;
  const said = { intentVerified: true, sig: sig.state, keyId: intent.keyId };
  const samePub = !!prev && prev.pub === sig.pub;
  if (prev && prev.hash === hash && samePub) {
    return pJson(Object.assign({ ok: true, owner: owner, stored: [], skipped: ["unchanged"] }, said));
  }
  const age = prev && typeof prev.t === "number" ? now - prev.t : PROFILE_MIN_GAP_MS;
  if (prev && samePub && age < PROFILE_MIN_GAP_MS && body.boot !== true) {
    return pJson(Object.assign({ ok: true, owner: owner, stored: [], skipped: ["within 8 min"] }, said));
  }
  const today = dayOf(now);
  const n = prev && prev.day === today && typeof prev.n === "number" ? prev.n : 0;
  if (n >= PROFILE_DAY_CAP) return pRefuse("quota: " + PROFILE_DAY_CAP + " uploads a day for " + owner);
  const rec = { owner: owner, t: now, day: today, n: n + 1, hash: hash, stores: stores,
                intentVerified: true, keyId: intent.keyId, pub: sig.pub };
  if (intent.slot) rec.slot = intent.slot;
  rec.signedAt = signedAt;
  // #210 (GrokBot) - the stores the owner's PC could not send ride beside the record so the shadow can name them.
  // Only d2r_ store names, at most 40; anything else is left off (absent = an older console, UNKNOWN).
  const unsent = unsentOf(body.unsent);
  if (unsent) rec.unsent = unsent;
  try {
    await kv.put(key, JSON.stringify(rec), { expirationTtl: TTL_S });
  } catch (e) {
    return pRefuse(String((e && e.message) || e).slice(0, 140));
  }
  return pJson(Object.assign({ ok: true, owner: owner, stored: ["profile"], key: key }, said));
}

// v3880 (#27) - the profiles of the OTHER PCs he approved for this label ("split the rows"): each one's characters answer
// (and the world it was drawn in), only while its key is still in the ring and its stores still match their hash. A PC
// whose record is missing, corrupt or signed by a key no longer in the ring is left out, never served as the label's.
export const OTHER_STORES = ["d2r_api_chars_learned", "d2r_api_world"];
async function othersOf(kv, owner, registered) {
  const out = [];
  for (const e of ringOf(registered)) {
    let rec = null;
    try { const raw = await kv.get(slotName(profileKeyOf(owner), e.slot)); rec = raw ? JSON.parse(raw) : null; } catch (x) { rec = null; }
    if (!rec || typeof rec !== "object" || rec.owner !== owner || rec.slot !== e.slot) continue;
    if (!storesOk(rec.stores) || rec.hash !== hashOfStores(rec.stores)) continue;
    if (b64uKey(rec.pub) !== b64uKey(e.pub)) continue;
    const stores = {};
    for (const k of OTHER_STORES) if (typeof rec.stores[k] === "string") stores[k] = rec.stores[k];
    out.push({ keyId: e.slot, t: rec.t, stores: stores });
  }
  return out;
}

async function profileGet(kv, owner) {
  if (!kv) return pJson({ ok: false, why: "profile could not be read: storage unavailable" });
  if (OWNERS.indexOf(owner) === -1) return pJson({ ok: false, why: "ask for one of the owner labels" });
  let prev = null;
  try {
    const raw = await kv.get(profileKeyOf(owner));
    prev = raw ? JSON.parse(raw) : null;
  } catch (e) {
    return pJson({ ok: false, why: "profile could not be read: " + String((e && e.message) || e).slice(0, 140) });
  }
  if (!prev || typeof prev !== "object" || prev.owner !== owner) {
    return pJson({ ok: true, owner: owner, published: false });
  }
  if (!storesOk(prev.stores) || prev.hash !== hashOfStores(prev.stores)) {
    return pJson({ ok: true, owner: owner, published: true, corrupt: true, t: prev.t });
  }
  // A record signed by a key that is no longer this owner's registered one is not served as theirs.
  let registered = null;
  try { registered = await registeredOf(kv, owner); } catch (e) {
    return pJson({ ok: false, why: "profile could not be read: the registered key could not be read" });
  }
  if (!signedByRegisteredNow(registered, prev)) {
    return pJson({ ok: true, owner: owner, published: true, corrupt: true, t: prev.t,
                  why: "the key that signed it is not " + owner + "'s registered key now" });
  }
  const out = { ok: true, owner: owner, published: true, corrupt: false, t: prev.t, hash: prev.hash,
                stores: prev.stores, intentVerified: prev.intentVerified === true };
  if (typeof prev.keyId === "string" && /^[0-9a-f]{12}$/.test(prev.keyId)) out.keyId = prev.keyId;
  const unsent = unsentOf(prev.unsent);
  if (unsent) out.unsent = unsent;
  const others = await othersOf(kv, owner, registered);
  if (others.length) out.others = others;
  return pJson(out);
}

// ── FRAMES: the owner's sessions, summarized, for shadow mode's Shelf and TV·D (#218 phase 2) ──────────────────
// His ruling 2026-10-28: a shadow renders the owner's data one to one, with SUMMARIZED frames - "a few small key frames
// per session" (a full reel is 8-12 GB and never leaves its PC; the profile still refuses every picture). v3894
// (Elad, 2026-11-10): those key frames and evidence are the 1920x1080 film itself, not 160 px thumbs the theatre
// then magnifies. This record is the ONE place a picture rides: at most 3 film-size JPEGs per session, 16 sessions,
// each under 800 KB - checked here, never trusted from the sender. Same key, intent and replay rule as the profile.
const FRAMES_MAX_BODY = 18874368;           // v3894: 18 MB — 16 sessions x 3 film-size JPEGs + witnesses
const FRAMES_DAY_CAP = 24;                      // v3862 paid: the console posts at most hourly (was 8 a day)
const FRAMES_MIN_GAP_MS = 50 * 60 * 1000;       // the worker refuses only inside 50 min (the console waits 60)
const FRAMES_MAX_SESSIONS = 16;
const FRAMES_MAX_PER = 3;
const FRAMES_MAX_WITNESS = 8;   // v3859 (b) - shadow_sessions.WITNESS_MAX
const FRAMES_MAX_JPG_B64 = 1100000;        // v3894: 800 KB of JPEG, base64 (was 20 KB / 160 px)
const SID_RX = /^s_\d{13}_\d{1,6}$/;
const FID_RX = /^\d{1,6}_\d{13}$/;

function framesKeyOf(owner) {
  return "roster:" + owner + ":frames";
}

function nOrNull(v) {
  return v === null || (typeof v === "number" && Number.isFinite(v) && v >= 0);
}

// -> null when the digest has exactly the shape shadow_sessions.digest builds, else why it does not
export function framesWhy(d) {
  if (!d || typeof d !== "object" || Array.isArray(d)) return "the digest is not an object";
  const ss = d.sessions;
  if (!Array.isArray(ss) || ss.length > FRAMES_MAX_SESSIONS) return "sessions must be a list of at most " + FRAMES_MAX_SESSIONS;
  for (const s of ss) {
    if (!s || typeof s !== "object" || Array.isArray(s)) return "a session is not an object";
    if (!(s.sessionId === null || (typeof s.sessionId === "string" && SID_RX.test(s.sessionId)))) return "a session id is not one";
    if (!nOrNull(s.t0) || !nOrNull(s.t1) || !(Number.isInteger(s.reads) && s.reads >= 0)) return "a session's times or reads are not numbers";
    if (!Array.isArray(s.names) || s.names.length > 8 || s.names.some((n) => typeof n !== "string" || n.length > 80)) {
      return "a session's names are not at most 8 short strings";
    }
    if (!(s.why === null || (typeof s.why === "string" && s.why.length <= 400))) return "a session's why is not a short string";
    if (!Array.isArray(s.frames) || s.frames.length > FRAMES_MAX_PER) return "a session carries more than " + FRAMES_MAX_PER + " frames";
    for (const f of s.frames) {
      if (!f || typeof f !== "object" || !FID_RX.test(String(f.id || ""))) return "a frame id is not a read frame's";
      if (typeof f.jpg !== "string" || f.jpg.length > FRAMES_MAX_JPG_B64 || f.jpg.indexOf("/9j/") !== 0
          || !/^[A-Za-z0-9+/]+={0,2}$/.test(f.jpg)) {
        return "a frame is not a small JPEG thumbnail";
      }
    }
  }
  // v3859 (b) item 18 - the vault's witnessed frames ride the digest: read frames' small JPEGs, at most FRAMES_MAX_WITNESS
  if (d.witness !== undefined) {
    if (!Array.isArray(d.witness) || d.witness.length > FRAMES_MAX_WITNESS) return "witness must be a list of at most " + FRAMES_MAX_WITNESS;
    for (const f of d.witness) {
      if (!f || typeof f !== "object" || !FID_RX.test(String(f.id || ""))) return "a witness id is not a read frame's";
      if (typeof f.jpg !== "string" || f.jpg.length > FRAMES_MAX_JPG_B64 || f.jpg.indexOf("/9j/") !== 0
          || !/^[A-Za-z0-9+/]+={0,2}$/.test(f.jpg)) {
        return "a witness frame is not a small JPEG thumbnail";
      }
    }
  }
  if (d.witnessWhy !== undefined) {
    const ww = d.witnessWhy;
    if (!ww || typeof ww !== "object" || Array.isArray(ww) || Object.keys(ww).length > 40
        || Object.entries(ww).some(([k, v]) => !FID_RX.test(k) || typeof v !== "string" || v.length > 160)) {
      return "witnessWhy must map read frame ids to short reasons";
    }
    if (privateIn(JSON.stringify(ww))) return "the digest carries a path, an install id or a token";
  }
  const text = JSON.stringify(ss.map((s) => Object.assign({}, s, { frames: s.frames.map((f) => f.id) })));
  if (privateIn(text)) return "the digest carries a path, an install id or a token";
  return null;
}

async function framesPost(env, bytes, sig, body) {
  const kv = env && env.TZ_HISTORY;
  if (!kv) return pRefuse("storage unavailable");
  if (bytes.byteLength > FRAMES_MAX_BODY) return pRefuse("the body is larger than " + FRAMES_MAX_BODY + " bytes");
  const owner = body.owner;
  if (OWNERS.indexOf(owner) === -1) return pRefuse("the key is an owner label, not a machine");
  const intent = await signedOwnerIntent(kv, owner, sig);
  if (intent instanceof Response) return intent;
  const why = framesWhy(body.digest);
  if (why) return pRefuse(why);
  const hash = hashOf(stable(body.digest));
  if (hash !== body.hash) return pRefuse("the digest does not match the hash that was signed");
  const key = slotName(framesKeyOf(owner), intent.slot);   // v3880 (#27) - another PC of this label: its own digest
  let prev = null;
  try {
    const raw = await kv.get(key);
    prev = raw ? JSON.parse(raw) : null;
  } catch (e) {
    return pRefuse("the stored frames could not be read");
  }
  if (!prev || typeof prev !== "object" || prev.owner !== owner) prev = null;
  const now = Date.now();
  const stale = signedAtRefusal(now, body.signedAt, prev);
  if (stale) return stale;
  const said = { intentVerified: true, sig: sig.state, keyId: intent.keyId };
  const samePub = !!prev && prev.pub === sig.pub;
  if (prev && prev.hash === hash && samePub) {
    return pJson(Object.assign({ ok: true, owner: owner, stored: [], skipped: ["unchanged"] }, said));
  }
  const age = prev && typeof prev.t === "number" ? now - prev.t : FRAMES_MIN_GAP_MS;
  if (prev && samePub && age < FRAMES_MIN_GAP_MS && body.boot !== true) {
    return pJson(Object.assign({ ok: true, owner: owner, stored: [], skipped: ["within 50 min"] }, said));
  }
  const today = dayOf(now);
  const n = prev && prev.day === today && typeof prev.n === "number" ? prev.n : 0;
  if (n >= FRAMES_DAY_CAP) return pRefuse("quota: " + FRAMES_DAY_CAP + " frames uploads a day for " + owner);
  const rec = { owner: owner, t: now, day: today, n: n + 1, hash: hash, digest: body.digest,
                intentVerified: true, keyId: intent.keyId, pub: sig.pub, signedAt: body.signedAt };
  try {
    await kv.put(key, JSON.stringify(rec), { expirationTtl: TTL_S });
  } catch (e) {
    return pRefuse(String((e && e.message) || e).slice(0, 140));
  }
  return pJson(Object.assign({ ok: true, owner: owner, stored: ["frames"], key: key }, said));
}

async function framesGet(kv, owner) {
  if (!kv) return pJson({ ok: false, why: "frames could not be read: storage unavailable" });
  if (OWNERS.indexOf(owner) === -1) return pJson({ ok: false, why: "ask for one of the owner labels" });
  let prev = null;
  try {
    const raw = await kv.get(framesKeyOf(owner));
    prev = raw ? JSON.parse(raw) : null;
  } catch (e) {
    return pJson({ ok: false, why: "frames could not be read: " + String((e && e.message) || e).slice(0, 140) });
  }
  if (!prev || typeof prev !== "object" || prev.owner !== owner) return pJson({ ok: true, owner: owner, published: false });
  if (framesWhy(prev.digest) || prev.hash !== hashOf(stable(prev.digest))) {
    return pJson({ ok: true, owner: owner, published: true, corrupt: true, t: prev.t });
  }
  let registered = null;
  try { registered = await registeredOf(kv, owner); } catch (e) {
    return pJson({ ok: false, why: "frames could not be read: the registered key could not be read" });
  }
  if (!signedByRegisteredNow(registered, prev)) {
    return pJson({ ok: true, owner: owner, published: true, corrupt: true, t: prev.t,
                  why: "the key that signed them is not " + owner + "'s registered key now" });
  }
  return pJson({ ok: true, owner: owner, published: true, corrupt: false, t: prev.t, hash: prev.hash,
                 digest: prev.digest, intentVerified: prev.intentVerified === true });
}
