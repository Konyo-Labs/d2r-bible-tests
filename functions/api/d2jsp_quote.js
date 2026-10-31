/**
 * /api/d2jsp_quote — a public reading of forum gold for one item.
 *
 * The bible cannot read forums.d2jsp.org from the browser (no CORS). This
 * function fetches the board 268 search and returns the middle
 * fg price only when a line that names the item carries an fg number.
 * A challenge page, a login wall, a failed fetch, or a page with no such
 * line returns fg:null. It never substitutes a remembered or default price.
 *
 * Board 268 is D2:R RotW Softcore Trading (non-ladder), the board the search reads (v3843; it was 243, Switch Ladder).
 * Posts still go to board 268. The two are different economies.
 */

const CORS = {
  'Access-Control-Allow-Origin': 'https://bull-4-u.com',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};
const BOARD = 268;

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status: status || 200,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      ...CORS,
    },
  });
}

/* ⟦D2JSP QUOTE BEGIN⟧ */
var D2JSP_QUOTE_BOARD = 268;
/* v3843 - ONLY RECENT POSTS PRICE AN ITEM. A price line counts only under a post dated within the last
   D2JSP_QUOTE_WINDOW_DAYS days of the reading (its readAt, else now) - a rolling window, so prices do not stop on
   Jan 1. A page that dates nothing, or only older posts, reads 'no prices' and the desk says unknown. */
var D2JSP_QUOTE_WINDOW_DAYS = 120;
var D2JSP_DAY_MS = 86400000;

/* v3843 - THE D2JSP LEXICON: the trade forum's own short names (its guides' slang and notation, never their prices).
   Each item maps to the words traders write for it; the search asks with the first, and a price line naming any
   form counts. */
var D2JSP_SLANG = {
  "Annihilus": ["anni"], "Hellfire Torch": ["torch"], "Gheed's Fortune": ["gheeds"],
  "Harlequin Crest": ["shako"], "Griffon's Eye": ["gface", "griffons"], "Crown of Ages": ["coa"],
  "Arreat's Face": ["arreats"], "Andariel's Visage": ["andy"], "Herald of Zakarum": ["hoz"],
  "Jalal's Mane": ["jalals"], "Stone of Jordan": ["soj"],
  "Bul-Kathos' Wedding Band": ["bk", "bk ring"], "Raven Frost": ["raven"], "Mara's Kaleidoscope": ["maras"],
  "Highlord's Wrath": ["highlords"], "Crown of Thieves": ["cot"], "Nightwing's Veil": ["nightwing", "veil"],
  "Mang Song's Lesson": ["mang song", "mangs"], "Eschuta's Temper": ["eschutas"], "Death's Fathom": ["fathom"],
  "Call to Arms": ["cta"], "Breath of the Dying": ["botd"], "Heart of the Oak": ["hoto"],
  "Hand of Justice": ["hoj"], "Enigma": ["nigma"], "Infinity": ["infy"], "Insight": [],
  "Grief": [], "Spirit": [], "Heart of Winter": [], "Fortitude": ["forti"],
  "Stormshield": ["storm shield"], "Death's Web": ["deathweb"], "Titan's Revenge": ["titans"],
  "Windforce": ["wf"], "Eaglehorn": [], "War Traveler": ["war travs", "wartravs"], "Waterwalk": [],
  "Sandstorm Trek": ["treks"], "Shadow Dancer": ["sdancer"], "Gore Rider": ["gores"],
  "Steelrend": ["rends"], "Magefist": ["mages"], "Dracul's Grasp": ["dracs"], "Bloodfist": ["bfists"],
  "Chance Guards": ["chancies"], "Arachnid Mesh": ["arach", "arachnid"], "Verdungo's Hearty Cord": ["dungo"],
  "Thundergod's Vigor": ["tgod"], "String of Ears": ["soe"], "Nosferatu's Coil": ["nos", "nosferatus"],
  "The Oculus": ["occy", "oculus"], "Spirit Ward": [],
  "Tyrael's Might": ["tyraels"], "Skullder's Ire": ["skullders"], "Vipermagi": ["viper", "vmagi"],
  "Shaftstop": ["shaft"], "Leviathan": ["levi"], "Guardian Angel": ["ga"], "Blackhorn's Face": ["bhades"],
  "Gladiator's Bane": ["glads"], "Templar's Might": ["templars"], "Atma's Scarab": ["atmas"],
  "Metalgrid": ["mgrid"], "Seraph's Hymn": ["seraphs"],
  "Doombringer": ["doom"], "Death Cleaver": ["dc"], "Executioner's Justice": ["ej"],
  "The Reaper's Toll": ["reapers"], "Stormlash": [], "Tomb Reaver": ["reaver"],
  "Grandfather": ["gf sword"], "Azurewrath": ["azure"], "Lightsabre": ["lsabre"],
  "Hellslayer": [], "Messerschmidt's Reaver": ["messer"], "Rainbow Facet": ["facet"],
  /* v3847 (Elad 15:42) - more of the forum's names; the first word is what the search box is given */
  "Guardian's Thunder": ["guardians thunder", "gt"], "Jeweler's Monarch of Deflecting": ["jmod"],
  "Doom": ["doom rw"], "Chains of Honor": ["coh"], "Phoenix": ["phoenix rw"], "Last Wish": ["lw"], "Faith": [],
  "Beast": [], "Exile": [], "Dream": [], "Fury": [], "Pride": [], "Silence": [],
  "Crescent Moon": ["cmoon"], "Bramble": [], "Destruction": [], "Obedience": ["obe"],
  "Whirlwind": ["ww"], "Vampire Gaze": ["vgaze"], "Wisp Projector": ["wisp"],
  "Dwarf Star": ["dwarf"], "Wizardspike": ["wspike", "spike"],
  "Ondal's Wisdom": ["ondals"], "Lidless Wall": ["lidless"], "Homunculus": ["homu"],
  "Arkaine's Valor": ["arkaines"], "Thunderstroke": ["tstroke"], "Kira's Guardian": ["kiras"],
  "Tal Rasha's Guardianship": ["tal armor"], "Sigon's Complete Steel": ["sigons"],
  "Immortal King's Stone Crusher": ["ik maul"], "Griswold's Honor": ["gris shield"]
};

/* v3847 (Elad 15:42) - A WORD THAT MEANS DIFFERENT ITEMS. Each entry lists its readings in order; a reading is taken
   when its context words are on the line (or in the search), and the LAST reading is the default. A post line whose
   context points at another reading does not count for this item. */
var D2JSP_AMBIG = {
  "doom": [{ item: "Doom", ctx: /\b(?:rw|runeword|cv|voulge|thresher|gt|polearm|pole|merc|eth)\b/ },
           { item: "Doombringer", ctx: /\b(?:sword|champion|unique|db)\b/ }, { item: "Doom", ctx: null }],
  "gt": [{ item: "Doom", ctx: /\b(?:doom|rw|runeword|thresher|polearm|base)\b/ },
         { item: "Guardian's Thunder", ctx: null }],
  "facet": [{ item: "Rainbow Facet", ctx: null }],
  "veil": [{ item: "Nightwing's Veil", ctx: null }],
  "storm": [{ item: "Stormshield", ctx: /\b(?:shield|monarch|ss)\b/ }, { item: "Stormlash", ctx: /\b(?:flail|lash)\b/ },
            { item: "Stormshield", ctx: null }],
  "spike": [{ item: "Wizardspike", ctx: null }],
  "gf": [{ item: "Grandfather", ctx: /\b(?:sword|colossus blade|unique|gfather)\b/ }, { item: null, ctx: null }]
};

/* -> {item, via, ambiguous}: the item a typed or written name means. A full name stays itself; a forum word becomes
   its item; an ambiguous word becomes the reading its context names (else its default). via says how it was read. */
function d2jspResolveItem(text, context) {
  var f = d2jspFoldPrice(text).replace(/[^a-z0-9 \-]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!f) return { item: '', via: 'empty', ambiguous: false };
  var ctx = ' ' + d2jspFoldPrice(context || text).replace(/[^a-z0-9]+/g, ' ') + ' ';
  var head = f.split(' ')[0];                       /* "doom cv": the first word, read by the rest */
  var key = Object.prototype.hasOwnProperty.call(D2JSP_AMBIG, f) ? f : (Object.prototype.hasOwnProperty.call(D2JSP_AMBIG, head) && f !== head ? head : null);
  if (key) {
    var rs = D2JSP_AMBIG[key];
    for (var i = 0; i < rs.length; i++) {
      if (!rs[i].ctx || rs[i].ctx.test(ctx)) return { item: rs[i].item || String(text), via: rs[i].ctx ? 'context' : 'default', ambiguous: rs.length > 1 };
    }
  }
  for (var k in D2JSP_SLANG) {
    if (!Object.prototype.hasOwnProperty.call(D2JSP_SLANG, k)) continue;
    var kf = d2jspSimpleName(k);
    if (kf === d2jspSimpleName(text)) return { item: k.trim(), via: 'name', ambiguous: false };
    if (D2JSP_SLANG[k].some(function (w) { return w === f; })) return { item: k.trim(), via: 'alias', ambiguous: false };
  }
  return { item: String(text).trim(), via: 'as typed', ambiguous: false };
}

/* true when a line that names an ambiguous form of itemName points, by a context word on it, at a different item
   (a bare ambiguous word with no context still counts: nothing on the line says otherwise) */
function d2jspOtherReading(line, itemName) {
  var folded = ' ' + d2jspFoldPrice(line).replace(/[^a-z0-9]+/g, ' ') + ' ', me = d2jspSimpleName(itemName);
  for (var w in D2JSP_AMBIG) {
    if (!Object.prototype.hasOwnProperty.call(D2JSP_AMBIG, w) || folded.indexOf(' ' + w + ' ') < 0) continue;
    if (folded.indexOf(' ' + me + ' ') >= 0) continue;          /* the full name is on the line: no doubt */
    var mine = D2JSP_AMBIG[w].some(function (r) { return r.item && d2jspSimpleName(r.item) === me; });
    if (!mine) continue;
    var r = d2jspResolveItem(w, line);
    if (r.via === 'context' && r.item && d2jspSimpleName(r.item) !== me) return true;   /* only a context word rules it out */
  }
  return false;
}

/* the guides' notation for mods: the short word and the plain words a seller means by it */
var D2JSP_NOTATION = {
  "@": "all resistances", "os": "open sockets", "eth": "ethereal", "ed": "enhanced damage", "dr": "damage reduced",
  "mdr": "magic damage reduced", "fcr": "faster cast rate", "fhr": "faster hit recovery", "frw": "faster run walk",
  "ias": "increased attack speed", "ll": "life leech", "ml": "mana leech", "lpl": "life per level",
  "lpk": "life per kill", "mpk": "mana per kill", "cb": "crushing blow", "gc": "grand charm", "lc": "large charm",
  "sc": "small charm", "perf": "perfect roll", "p": "perfect roll", "upd": "upgraded", "rand": "random roll",
  "unid": "unidentified", "igg": "in game gold", "pc": "poison charm", "pnb": "poison and bone",
  "cr": "cold resist", "fr": "fire resist", "lr": "lightning resist", "pr": "poison resist",
  "mf": "magic find", "gf": "gold find", "rep": "replenish", "res": "resistances", "req": "requirement",
  "str": "strength", "dex": "dexterity", "ar": "attack rating", "def": "defense", "dmg": "damage",
  "ow": "open wounds", "ls": "life stolen", "sorc": "sorceress", "sin": "assassin", "zon": "amazon",
  "barb": "barbarian", "dru": "druid", "nec": "necromancer", "pala": "paladin"
};

function d2jspSlangOf(itemName) {
  var f = d2jspFoldPrice(itemName);
  for (var k in D2JSP_SLANG) {
    if (Object.prototype.hasOwnProperty.call(D2JSP_SLANG, k) && d2jspFoldPrice(k) === f) return D2JSP_SLANG[k].slice();
  }
  return [];
}

/* the simplified name: no apostrophes, no leading "The", no "'s" */
function d2jspSimpleName(itemName) {
  return d2jspFoldPrice(String(itemName || '').replace(/['\u2018\u2019\u02BC`]s\b/gi, '')).replace(/^the\s+/, '').replace(/[^a-z0-9 \-]/g, ' ').replace(/\s+/g, ' ').trim();
}

/* the search words like a search box takes them: the slang form when traders have one, else the simplified name;
   every form a price line may name it by rides along in `forms` */
function d2jspSearchWords(itemName) {
  itemName = d2jspResolveItem(itemName).item || itemName;   /* v3847 - "gt", "anni", "jmod" search as their item */
  var slang = d2jspSlangOf(itemName), simple = d2jspSimpleName(itemName), full = d2jspFoldPrice(itemName);
  var forms = [];
  [full, simple].concat(slang).forEach(function (w) { if (w && forms.indexOf(w) < 0) forms.push(w); });
  return { query: slang.length ? slang[0] : simple, slang: slang, simple: simple, forms: forms };
}

/* the notation parser: "Anni 20/20/10 eth 2os @30 perf" -> slash tuples, socket count, ethereal, all res, perfect,
   upgraded, random, and each known short word in plain words */
function d2jspNotation(text) {
  var t = String(text || '');
  var out = { tuples: [], sockets: null, eth: false, perfect: false, upgraded: false, random: false, allRes: null, words: [] };
  var m, re = /(\d+(?:\/\d+)+)/g;
  while ((m = re.exec(t))) out.tuples.push(m[1].split('/').map(Number));
  if ((m = /\b(\d)\s*os\b/i.exec(t))) out.sockets = Number(m[1]);
  if ((m = /@\s*(\d+)|(\d+)\s*@/.exec(t))) out.allRes = Number(m[1] || m[2]);
  out.eth = /\beth\b/i.test(t);
  out.perfect = /\bperf(?:ect)?\b/i.test(t);
  out.upgraded = /\bup'?d\b|\bupped\b/i.test(t);
  out.random = /\brand\b/i.test(t);
  String(t).toLowerCase().replace(/'/g, '').split(/[^a-z@]+/).forEach(function (w) {
    if (w && Object.prototype.hasOwnProperty.call(D2JSP_NOTATION, w) && out.words.indexOf(D2JSP_NOTATION[w]) < 0) out.words.push(D2JSP_NOTATION[w]);
  });
  return out;
}

var D2JSP_MONTHS = 'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec';
/* the UTC day (ms) a line dates its post by, or null: "Oct 12, 2026", "12 Oct 2026", "2026-10-12", or Today /
   Yesterday (counted from nowMs) */
function d2jspLineDate(line, nowMs) {
  var t = String(line || ''), mon = D2JSP_MONTHS.split('|');
  var m = new RegExp('\\b(' + D2JSP_MONTHS + ')[a-z]*\\.?\\s+(\\d{1,2})(?:st|nd|rd|th)?,?\\s+(20\\d\\d)\\b', 'i').exec(t);
  if (m) return Date.UTC(Number(m[3]), mon.indexOf(m[1].toLowerCase()), Number(m[2]));
  m = new RegExp('\\b(\\d{1,2})\\s+(' + D2JSP_MONTHS + ')[a-z]*\\.?,?\\s+(20\\d\\d)\\b', 'i').exec(t);
  if (m) return Date.UTC(Number(m[3]), mon.indexOf(m[2].toLowerCase()), Number(m[1]));
  m = /\b(20\d\d)-(\d\d)-(\d\d)\b/.exec(t);
  if (m) return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (/\btoday\b/i.test(t)) return nowMs;
  if (/\byesterday\b/i.test(t)) return nowMs - D2JSP_DAY_MS;
  return null;
}
/* the reading's own clock: its readAt when that is a time, else now */
function d2jspNowMs(readAt) {
  var t = Date.parse(String(readAt || ''));
  return isFinite(t) ? t : Date.now();
}
/* a post dated `when` is recent for a reading at nowMs: inside the window, and not in the future past a day of clock skew */
function d2jspRecent(when, nowMs) {
  return when != null && when <= nowMs + D2JSP_DAY_MS && when >= nowMs - D2JSP_QUOTE_WINDOW_DAYS * D2JSP_DAY_MS;
}

function d2jspFoldPrice(text) {
  return String(text || '').replace(/['\u2018\u2019\u02BC`]/g, '').toLowerCase().replace(/\s+/g, ' ').trim();
}

/* v3843 - THE FG AMOUNTS ON A LINE, LARGE ONES INCLUDED. "300fg", "300 fg", "1,500 fg", "30,000fg", "1.5k", "25k fg",
   "10K". A comma groups thousands (before this "1,500 fg" read as 500). A bare "k" amount counts: the trade forum writes
   tens-of-thousands prices that way. Anything at or above 10,000,000 is not a price. */
function d2jspFgAmounts(line) {
  var out = [], m, re = /(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(k\b|k(?=\s*fg)|)\s*(fg\b)?/ig;
  while ((m = re.exec(String(line || '')))) {
    if (!m[2] && !m[3]) continue;
    var n = Number(m[1].replace(/,/g, ''));
    if (m[2]) n = Math.round(n * 1000);
    if (n > 0 && n < 10000000) out.push(n);
  }
  return out;
}

/* v3844 - 2026 POSTS ONLY (Elad, 2026-10-30): on top of the rolling window, no post dated before this day prices an item. */
var D2JSP_QUOTE_SINCE_MS = Date.UTC(2026, 0, 1);

/* v3844 - THE POST A PRICE CAME FROM. Before the tags are stripped, a link to a forum topic or post is kept as a marker,
   so every price line knows the post it sits under and the evidence drawer can open it. */
var D2JSP_LINK_MARK = /\u27e6L:([^\u27e7]*)\u27e7/g;
function d2jspAbsLink(href) {
  var h = String(href || '').replace(/&amp;/g, '&').trim();
  if (!h) return '';
  if (/^https:\/\/forums\.d2jsp\.org\//i.test(h)) return h;
  if (/^https?:/i.test(h)) return '';
  return 'https://forums.d2jsp.org/' + h.replace(/^\/+/, '');
}

/* v3844 - WHICH AMOUNTS ON A LINE ARE THIS ITEM'S. A line that names one thing and carries one price is that price. A
   line listing several items ("anni 5 ist, pc 2000 fg, torch 300 fg") is split into its clauses, and only an amount in
   a clause that names the item counts - before this, Annihilus read 5-2000 off other items' prices. v3845 (second eye
   on v3844): when the split tears the name itself apart so that NO clause names the item, though the line does, the
   line's amounts are not dropped - the line names the item, so they are its. */
function d2jspNamed(text, forms) {
  var folded = ' ' + d2jspFoldPrice(text).replace(/[^a-z0-9]+/g, ' ') + ' ';
  return forms.some(function (f) { return folded.indexOf(' ' + f.replace(/[^a-z0-9]+/g, ' ').trim() + ' ') >= 0; });
}

/* v3845 - COMPACT ROLL COLUMNS (Elad, 2026-10-30 09:29): "guardian's thunder +8 -9 4 40 28 140fg" is the item, then
   its rolls as bare numbers in the item's own mod order (signs and % kept), then the price. Each clause that names the
   item gives its price with the numbers written between the name and that price; the desk maps them onto the mods. */
function d2jspAfterName(clause, forms) {
  var low = d2jspFoldPrice(clause), at = -1, len = 0;
  forms.forEach(function (f) {
    var re = new RegExp('(^|[^a-z0-9])' + f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/ /g, '\\s+') + '(?=$|[^a-z0-9])');
    var m = re.exec(low);
    if (m && (at < 0 || m.index < at)) { at = m.index + m[1].length; len = m[0].length - m[1].length; }
  });
  return at < 0 ? null : low.slice(at + len);
}
function d2jspClauseCols(clause, forms) {
  var rest = d2jspAfterName(clause, forms);
  if (rest == null) return null;
  var cut = /(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:k\b|k(?=\s*fg)|fg\b)/i.exec(rest);
  var head = cut ? rest.slice(0, cut.index) : rest, toks = head.trim().split(/\s+/), cols = [];
  for (var i = 0; i < toks.length; i++) {
    var m = /^([+-]?\d{1,4})%?$/.exec(toks[i]);
    if (!m) { if (cols.length) break; else continue; }
    cols.push(Number(m[1]));
  }
  return cols.length >= 2 && cols.length <= 8 ? cols : null;
}
function d2jspLineRows(line, forms) {
  var all = d2jspFgAmounts(line);
  if (!all.length) return [];
  var clauses = all.length <= 1 ? [String(line)] : String(line).split(/\s*(?:[;|\u2022]|,(?!\d{3}(?!\d)))\s*/), out = [];
  clauses.forEach(function (c) {
    if (all.length > 1 && !d2jspNamed(c, forms)) return;
    var cols = d2jspClauseCols(c, forms);
    d2jspFgAmounts(c).forEach(function (n) { out.push({ fg: n, cols: cols }); });
  });
  if (!out.length && d2jspNamed(line, forms) && !clauses.some(function (c) { return d2jspNamed(c, forms); })) {
    var cols = d2jspClauseCols(line, forms);
    all.forEach(function (n) { out.push({ fg: n, cols: all.length === 1 ? cols : null }); });
  }
  return out;
}

/* each price with its evidence: the post's link, its day, the fg and the roll as read (the slash
   notation). The post's own words stay on the forum - the link opens them. */
/* v3847 - the page's HTML entities, decoded once, after the tags are gone (so a decoded "<" can never open a tag). */
function d2jspDecodeEntities(t) {
  var named = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', rsquo: '\u2019', lsquo: '\u2018',
                ldquo: '\u201c', rdquo: '\u201d', ndash: '-', mdash: '-', hellip: '...' };
  return String(t).replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, function (all, k) {
    if (k[0] === '#') {
      var n = k[1] === 'x' || k[1] === 'X' ? parseInt(k.slice(2), 16) : parseInt(k.slice(1), 10);
      return n > 0 && n < 0x110000 ? String.fromCodePoint(n) : all;
    }
    var v = named[k.toLowerCase()];
    return v == null ? all : v;
  });
}

function d2jspPosts(text, itemName, nowMs, aside) {
  if (nowMs == null) nowMs = Date.now();
  var forms = d2jspSearchWords(itemName).forms;
  if (!forms.length) return [];
  var plain = String(text || '')
    .replace(/<a\s[^>]*href\s*=\s*["']([^"']*(?:topic\.php|[?&]t=\d|[?&]p=\d)[^"']*)["'][^>]*>/gi, ' \u27e6L:$1\u27e7 ')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(?:p|div|tr|li|h\d)>/gi, '\n')
    /* v3847 (Elad 15:27, Guardian's Thunder read 0 posts) - search highlighting wraps the matched word in an inline tag
       (<b>guardian</b>'s); turning that tag into a space made "guardian 's", which no item form matches. An inline tag
       is unwrapped with NO space; every other tag still becomes one. */
    .replace(/<\/?(?:b|i|u|em|strong|span|font|mark|small|big)(?:\s[^>]*)?>/gi, '')
    .replace(/<[^>]+>/g, ' ');
  plain = d2jspDecodeEntities(plain);   /* v3847 - &#39; / &rsquo; / &amp; arrive raw: Guardian&#39;s matched nothing */
  var rows = [], when = null, link = '', explicit = false;
  plain.split('\n').forEach(function (raw) {
    var m, re = new RegExp(D2JSP_LINK_MARK.source, 'g');
    var here = '';
    while ((m = re.exec(raw))) { var a = d2jspAbsLink(m[1]); if (a) here = a; }
    var line = raw.replace(new RegExp(D2JSP_LINK_MARK.source, 'g'), ' ');
    var d = d2jspLineDate(line, nowMs);
    /* v3845 (second eye on v3844) - a new post's date line starts a new post: the last post's link does not carry over */
    /* v3845 - a post's own written date beats a relative "Today" / "Yesterday" (the search page's last-activity
       stamp): Simsalara's Oct 7 post read as the reading's day. A relative stamp dates a post only when that post has
       no written date of its own. */
    var rel = d != null && !/\b20\d\d\b/.test(line) && /\b(?:today|yesterday)\b/i.test(line);
    if (d != null && !rel) { when = d; explicit = true; link = here; }          /* a written date starts a post */
    else if (here && here !== link) { link = here; when = rel ? d : null; explicit = false; }   /* so does a new post link */
    else if (rel && !explicit) when = d;
    else if (here) link = here;
    /* v3843 - a price counts only under a recently dated post; v3844 - and only a 2026 one */
    /* v3847 (Elad 15:27) - a line that names the item and is NOT priced is kept with the reason, for the drawer: a
       reading of 0 priced posts still shows what was read and why each was set aside. Never weighed (w 0). */
    var named = d2jspNamed(line, forms) && !d2jspOtherReading(line, d2jspResolveItem(itemName).item || itemName);
    if (!d2jspRecent(when, nowMs) || when < D2JSP_QUOTE_SINCE_MS) {
      if (named && aside) aside.push({ link: link,
        day: when ? new Date(when).toISOString().slice(0, 10) : '',
        why: when == null ? 'no post date read' : 'older than the price window' });
      return;
    }
    if (!named) return;
    var note = d2jspNotation(line);
    var lr = d2jspLineRows(line, forms);
    if (!lr.length && aside) aside.push({ link: link,
      day: new Date(when).toISOString().slice(0, 10), why: 'no fg price on the line' });
    lr.forEach(function (x) {
      var row = { fg: x.fg, day: new Date(when).toISOString().slice(0, 10), link: link,
        roll: note.tuples, mods: note.words.slice(0, 12), w: 1 };
      if (x.cols) row.cols = x.cols;
      if (note.perfect) row.perfect = true;   /* v3849 - the post says perf/perfect: the price DB keeps a perfect tier */
      rows.push(row);
    });
  });
  return d2jspTrim(rows);
}

/* v3844 - A FAR PRICE IS SET ASIDE. With five or more prices, one more than three times off the middle (a 2000 fg
   bundle beside 18 fg singles) is kept in the evidence, marked out, and does not move the price. */
function d2jspTrim(rows) {
  if (rows.length < 5) return rows;
  var mid = d2jspMedian(rows.map(function (r) { return r.fg; }));
  /* v3845 - a post that writes its roll is not judged by the middle: its roll may be why it is far (the -10 jewel at
     390 fg). The desk fits price against roll and sets such a post aside only when its roll does not explain it. */
  /* v3847 (#230 6524232951) - THE SAME RULE FOR A SLASH ROLL. "anni 20/20/10 1200fg" was set aside as far from the
     middle while its roll was why. A post that writes a slash roll is judged against a price-by-roll fit over the posts
     that write a roll of the same shape, and set aside only when its roll does not explain its price (3x off the fit).
     Too few such posts to fit: it is kept, never judged by the middle. */
  var fit = d2jspSlashFit(rows);
  rows.forEach(function (r) {
    if (r.cols) return;
    var t = d2jspSlashOf(r);
    if (t) {
      var f = fit[t.length];
      if (!f) return;
      var e = f.at(t);
      if (r.fg > e * 3 || r.fg * 3 < e) { r.w = 0; r.out = 'far from the middle: its roll does not explain its price (fit ' + Math.round(e) + ' fg)'; }
      return;
    }
    if (r.fg > mid * 3 || r.fg * 3 < mid) { r.w = 0; r.out = 'far from the middle ' + mid + ' fg'; }
  });
  return rows;
}

/* v3849 - A NO-ROLL PRICE 10x OFF THE CLOSE FIT. The 3x rule above still marks a far price out loud.
   This one is quiet and extra: only posts that wrote a roll (columns or a slash) set the middle, and
   only when at least three of them did. A post with no roll that is more than 10x off that middle, or
   under a tenth of it, is set aside (w 0) and counted. It does not grow a new "far from the middle"
   label. The price line says "n lines skipped" once. */
function d2jspGrossSkip(rows) {
  var close = (rows || []).filter(function (r) { return r && (r.cols || d2jspSlashOf(r)); });
  if (close.length < 3) return 0;
  var mid = d2jspMedian(close.map(function (r) { return r.fg; }));
  if (!(mid > 0)) return 0;
  var n = 0;
  rows.forEach(function (r) {
    if (r.cols || d2jspSlashOf(r)) return;
    if (r.fg > mid * 10 || r.fg * 10 < mid) { r.w = 0; n++; }
  });
  return n;
}

/* the post's first slash roll (2+ numbers), or null */
function d2jspSlashOf(r) {
  var t = (r.roll || []).filter(function (x) { return x && x.length >= 2; })[0];
  return t ? t.map(Number) : null;
}

/* {length: {at(t)}} - per roll shape with 5+ posts: ln(fg) = a + b * place, place = the roll's mean position between
   the lowest and highest value each column takes in these posts (0..1). */
function d2jspSlashFit(rows) {
  var by = {}, out = {};
  rows.forEach(function (r) { var t = d2jspSlashOf(r); if (t && r.fg > 0) (by[t.length] = by[t.length] || []).push({ t: t, fg: r.fg }); });
  Object.keys(by).forEach(function (L) {
    var pts = by[L];
    if (pts.length < 5) return;
    var lo = [], hi = [];
    for (var i = 0; i < +L; i++) {
      lo.push(Math.min.apply(null, pts.map(function (p) { return p.t[i]; })));
      hi.push(Math.max.apply(null, pts.map(function (p) { return p.t[i]; })));
    }
    var place = function (t) {
      var s = 0, n = 0;
      for (var i = 0; i < t.length; i++) if (hi[i] > lo[i]) { s += Math.max(0, Math.min(1, (t[i] - lo[i]) / (hi[i] - lo[i]))); n++; }
      return n ? s / n : 0.5;
    };
    var xs = pts.map(function (p) { return place(p.t); }), ys = pts.map(function (p) { return Math.log(p.fg); });
    /* fit, drop the one point furthest past 3x, refit: one 2000 fg bundle must not drag the line onto the others */
    var keep = xs.map(function () { return true; }), a = 0, b = 0;
    for (;;) {
      var ix = [], k;
      for (k = 0; k < xs.length; k++) if (keep[k]) ix.push(k);
      var mx = ix.reduce(function (s, k) { return s + xs[k]; }, 0) / ix.length, my = ix.reduce(function (s, k) { return s + ys[k]; }, 0) / ix.length;
      var sxx = 0, sxy = 0;
      ix.forEach(function (k) { sxx += (xs[k] - mx) * (xs[k] - mx); sxy += (xs[k] - mx) * (ys[k] - my); });
      b = sxx > 1e-9 ? sxy / sxx : 0; a = my - b * mx;
      var worst = -1, far = Math.log(3);
      ix.forEach(function (k) { var d = Math.abs(ys[k] - (a + b * xs[k])); if (d > far) { far = d; worst = k; } });
      if (worst < 0 || ix.length <= 4) break;
      keep[worst] = false;
    }
    out[L] = { at: function (t) { return Math.exp(a + b * place(t)); } };
  });
  return out;
}

function d2jspPrices(text, itemName, nowMs) {
  return d2jspPosts(text, itemName, nowMs).filter(function (r) { return r.w > 0; }).map(function (r) { return r.fg; });
}

function d2jspMedian(nums) {
  if (!nums || !nums.length) return null;
  var s = nums.slice().sort(function (a, b) { return a - b; });
  var mid = Math.floor(s.length / 2);
  if (s.length % 2) return s[mid];
  return Math.round((s[mid - 1] + s[mid]) / 2);
}

function d2jspSpan(nums) {
  if (!nums || !nums.length) return { low: null, high: null };
  var s = nums.slice().sort(function (a, b) { return a - b; });
  return { low: s[0], high: s[s.length - 1] };
}

function d2jspRead(html, item, readAt) {
  var text = String(html || '');
  var base = {
    item: String(item || ''), fg: null, low: null, high: null,
    n: 0, readAt: readAt, reason: 'unread', board: D2JSP_QUOTE_BOARD
  };
  if (!text || /Just a moment/i.test(text) || /cf-browser-verification/i.test(text)) return base;
  if (/do not have permission/i.test(text) || /not currently logged in/i.test(text)) {
    base.reason = 'need-login';
    return base;
  }
  var aside = [];
  var posts = d2jspPosts(text, item, d2jspNowMs(readAt), aside);
  var skipped = d2jspGrossSkip(posts);
  var nums = posts.filter(function (r) { return r.w > 0; }).map(function (r) { return r.fg; });
  var fg = d2jspMedian(nums);
  if (fg == null) {
    base.reason = 'no prices';
    base.posts = posts.slice(0, 40);        /* v3847 - the drawer shows what was read even with no price */
    base.aside = aside.slice(0, 40);
    if (skipped > 0) base.skipped = skipped;
    return base;
  }
  var span = d2jspSpan(nums);
  var read = {
    item: String(item || ''), fg: fg, low: span.low, high: span.high,
    n: nums.length, readAt: readAt, reason: 'read', board: D2JSP_QUOTE_BOARD,
    posts: posts.slice(0, 40), aside: aside.slice(0, 40)
  };
  if (skipped > 0) read.skipped = skipped;
  return read;
}
/* ⟦D2JSP QUOTE END⟧ */

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const item = (url.searchParams.get('item') || '').trim().slice(0, 80);
  const readAt = new Date().toISOString();
  if (!item) return json({ item: '', fg: null, n: 0, readAt: readAt, reason: 'no item', board: BOARD });
  const keywords = d2jspSearchWords(item).query || String(item).replace(/['\u2018\u2019\u02BC`]/g, '');
  const search = 'https://forums.d2jsp.org/search.php?sr=posts&search_keywords='
    + encodeURIComponent(keywords) + '&fid%5B%5D=' + BOARD;
  try {
    const r = await fetch(search, {
      headers: {
        'User-Agent': 'KonyoD2RBible/1.0 (+https://bull-4-u.com/d2r/)',
        Accept: 'text/html',
      },
    });
    if (!r.ok) return json(d2jspRead('', item, readAt));
    const html = await r.text();
    return json(d2jspRead(html.slice(0, 200000), item, readAt));
  } catch (e) {
    return json(d2jspRead('', item, readAt));
  }
}
