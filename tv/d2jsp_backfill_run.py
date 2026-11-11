# -*- coding: utf-8 -*-
"""#151 - THE READ-ONLY d2jsp PRICE BACKFILL RUNNER, IN THE TREE (REG-3795).

It ran from a private run folder until v3899, and that folder's own copies of d2jsp_backfill.py / d2jsp_price_db.py came
FIRST on sys.path - a fix shipped here never reached the run. It now lives beside the modules it drives; the run folder
holds only data (items.json, progress-shard*.json, prices-shard*.json, results-urls-shard*.json, pages/, the log).

Signed-in GET/search only, forum 268, ONE search per minute, resumable. Never posts, trades, PMs, or clicks a
compose/edit control. Never prints cookies, session values, tokens, or raw pages. Never writes the console's live
d2jsp_price_db.json while it runs: --import-into is a separate, offline step.

  backfill / resume   python3 tv/d2jsp_backfill_run.py --root RUN --repo REPO --shard 0 --shards 1
  monthly refresh     ... --refresh      (re-opens only items last read over 30 days ago; same 1/min pace)
  import              python3 tv/d2jsp_backfill_run.py --root RUN --repo REPO --shard 0 --shards 1 \
                          --import-into REPO/tv/d2jsp_price_db.json [--dry-run]   (no network, no sign-in)
  seller check        ... --check-authors (reads the kept pages/ only: how many topics name their seller)
  stop                create RUN/STOP. A challenge or rate-limit page writes RUN/CHALLENGE and exits 2; nothing is
                      asked again while that file is there - his look first, never a bypass.
"""
from __future__ import print_function

import argparse
import datetime
import json
import os
import re
import sys
import time
import traceback

SEARCH_GAP_S = 60.0
CUTOFF_YEARS = 2
FORUM = 268
SHARDS = 2
HERE = os.path.dirname(os.path.abspath(__file__))
CONSOLE_DB_QUIET_S = 60.0

# Bare rune names. Searching "ber rune" misses posts; the forum query is just "ber".
RUNE_NAMES = [
    "El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort", "Thul",
    "Amn", "Sol", "Shael", "Dol", "Hel", "Io", "Lum", "Ko", "Fal", "Lem",
    "Pul", "Um", "Mal", "Ist", "Gul", "Vex", "Ohm", "Lo", "Sur", "Ber",
    "Jah", "Cham", "Zod",
]
RUNE_KEYS = set(n.lower() for n in RUNE_NAMES)


def bare_rune_query(item):
    """'Ber Rune' / 'ber rune' / 'Ber' -> 'Ber'. Anything else -> None."""
    s = str(item or "").strip()
    if not s:
        return None
    m = re.match(r"^([A-Za-z]+)\s+rune$", s, re.I)
    if m and m.group(1).lower() in RUNE_KEYS:
        for n in RUNE_NAMES:
            if n.lower() == m.group(1).lower():
                return n
    if s.lower() in RUNE_KEYS:
        for n in RUNE_NAMES:
            if n.lower() == s.lower():
                return n
    return None


def install_bare_rune_search(C):
    """Wrap the live keyword helper so rune searches never go out as 'ber rune'."""
    if getattr(C, "_bare_rune_wrapped", False):
        return
    real = C._search_keywords

    def wrapped(item, node_run=None):
        bare = bare_rune_query(item)
        if bare:
            return bare
        words = real(item, node_run=node_run)
        stripped = bare_rune_query(words)
        return stripped or words

    C._search_keywords = wrapped
    C._bare_rune_wrapped = True


NEED_LOGIN_HTML = "<html>not currently logged in</html>"

_SCRUB_QS = re.compile(
    r"([?&;](?:s|sid|sess|session|token|k|key|hash)=)[^&\"'\s<>]+", re.I
)


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s IST] %s" % (ts, msg)
    print(line, flush=True)
    log_path = os.environ.get("D2JSP_BACKFILL_LOG")
    if log_path:
        try:
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass


def scrub_url(url):
    return _SCRUB_QS.sub(r"\1X", str(url or ""))


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def cutoff_date():
    return (utc_now() - datetime.timedelta(days=int(365.25 * CUTOFF_YEARS))).date()


def write_json(path, rec):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)


def read_json(path, default=None):
    if not path or not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def shard_items(items, shard, shards):
    out = []
    for i, name in enumerate(items):
        if i % shards == shard:
            out.append(name)
    return out


def inject_priority(rec, priority, in_progress_name=None):
    """Put the shard's priority names next in the queue.

    An item already being paged is left at the cursor so its offset is finished
    first. New priority names are inserted immediately after it (or at the cursor
    when nothing is mid-page). Existing later copies are removed so each name
    stays once. -> rec
    """
    if not isinstance(rec, dict):
        return rec
    queue = list(rec.get("queue") or [])
    pri = [str(x).strip() for x in (priority or []) if str(x).strip()]
    pri = [x for i, x in enumerate(pri) if x not in pri[:i]]
    if not pri:
        rec["queue"] = queue
        return rec
    try:
        cursor = int(rec.get("cursor") or 0)
    except (TypeError, ValueError):
        cursor = 0
    if queue:
        cursor = cursor % len(queue)
    insert_at = cursor
    current = in_progress_name
    if current is None and queue:
        current = queue[cursor]
        st = (rec.get("items") or {}).get(__import__("d2jsp_price_db").key_of(current))
        mid = isinstance(st, dict) and not st.get("done") and int(st.get("pages") or 0) > 0
        if not mid:
            current = None
    if current:
        # finish the mid-page item, then the priority group
        if current in queue:
            # keep current at cursor
            insert_at = queue.index(current) + 1
        else:
            queue.insert(cursor, current)
            insert_at = cursor + 1
    for name in pri:
        while name in queue:
            at = queue.index(name)
            queue.pop(at)
            if at < insert_at:
                insert_at -= 1
    for i, name in enumerate(pri):
        queue.insert(insert_at + i, name)
    rec["queue"] = queue
    if current and current in queue:
        rec["cursor"] = queue.index(current)
    elif pri and pri[0] in queue:
        rec["cursor"] = queue.index(pri[0])
    return rec


def load_catalog_full(root):
    path = os.path.join(root, "items.json")
    rec = read_json(path)
    if not isinstance(rec, dict) or not rec.get("items"):
        raise SystemExit("items.json is missing or empty in %s" % root)
    items = [str(x).strip() for x in rec["items"] if str(x).strip()]
    # de-dupe, keep first occurrence so the priority names stay at the front
    seen = set()
    out = []
    for n in items:
        k = n.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(n)
    pri = [str(x).strip() for x in (rec.get("priority") or []) if str(x).strip()]
    pri = [x for i, x in enumerate(pri) if x not in pri[:i]]
    by = {}
    raw_by = rec.get("priorityByShard") or {}
    if isinstance(raw_by, dict):
        for k, names in raw_by.items():
            by[str(k)] = [str(x).strip() for x in (names or []) if str(x).strip()]
    return {"items": out, "priority": pri, "priorityByShard": by}


def load_catalog(root):
    return load_catalog_full(root)["items"]


def stop_path(root):
    return os.path.join(root, "STOP")


def challenge_path(root):
    return os.path.join(root, "CHALLENGE")


def signed_out_path(root):
    return os.path.join(root, "SIGNED_OUT")


def want_stop(root):
    return os.path.exists(stop_path(root))


def write_flag(path, reason):
    rec = {
        "at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason": str(reason or "")[:240],
    }
    write_json(path, rec)


def pid_path(root):
    return os.path.join(root, "backfill.pid")


def write_pid(root):
    with open(pid_path(root), "w", encoding="utf-8") as fh:
        fh.write(str(os.getpid()) + "\n")


def setup_paths(root, repo):
    root = os.path.abspath(root)
    repo = os.path.abspath(repo)
    os.makedirs(root, exist_ok=True)
    pages = os.path.join(root, "pages")
    os.makedirs(pages, exist_ok=True)
    os.environ["D2JSP_PAGES_DIR"] = pages
    # REG-3795 - the modules come from the tree this runner sits in, never from copies in the run folder
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    return root, repo


def import_live_chrome():
    import d2jsp_chrome as C  # noqa: E402

    return C


def login_state(C):
    """Return {ok, state, kind, why} only. Never includes a cookie."""
    try:
        st = C.d2jsp_login_status()
    except Exception as e:
        return {
            "ok": False,
            "state": "unknown",
            "kind": "unread",
            "why": "login status raised %s" % type(e).__name__,
        }
    if not isinstance(st, dict):
        return {"ok": False, "state": "unknown", "kind": "unread", "why": "login status was not a dict"}
    return {
        "ok": st.get("ok") is True and st.get("state") == "on",
        "state": str(st.get("state") or "unknown")[:24],
        "kind": str(st.get("kind") or "")[:24],
        "why": str(st.get("why") or "")[:200],
    }


def is_challenge(html, C=None):
    text = str(html or "")
    if C is not None:
        try:
            if C._challenge_page(text):
                return True
        except Exception:
            pass
    low = text.lower()
    if "just a moment" in low or "cf-browser-verification" in low:
        return True
    if "too many requests" in low or "rate limit" in low:
        return True
    if "try again later" in low and "search" in low:
        return True
    if re.search(r"please (?:slow down|wait).{0,40}(search|request)", text, re.I):
        return True
    return False


def looks_rate_limited(html):
    text = str(html or "")
    return bool(
        re.search(
            r"too many requests|rate.?limit|you are (?:being )?rate|slow down|try again later",
            text,
            re.I,
        )
    )



def is_genuine_empty_results(html):
    """A real signed-in results page that found no posts (safe to mark last page)."""
    return bool(re.search(
        r"no (?:results|matches|topics)|did not match|returned 0|not find any|0 results",
        str(html or ""),
        re.I,
    ))


def is_hollow_results(html):
    """A JS shell or short 'Viewing Search Results' page with no topics — not a last page."""
    text = str(html or "")
    if not text.strip():
        return True
    if looks_rate_limited(text):
        return False
    if re.search(r"just a moment|cf-browser-verification", text, re.I):
        return False
    if re.search(r"not currently logged in|do not have permission", text, re.I):
        return False
    if re.search(r"topic\.php", text, re.I):
        return False
    if is_genuine_empty_results(text):
        return False
    if re.search(r"search results", text, re.I):
        return True
    return len(text) < 2000


def with_offset(url, offset):
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
    parts = list(urlparse(url))
    q = parse_qs(parts[4], keep_blank_values=True)
    q["o"] = [str(int(offset))]
    parts[4] = urlencode(q, doseq=True)
    return urlunparse(parts)


def results_url_from_html(html, C):
    text = str(html or "")
    found = None
    for m in re.finditer(r"""href=["']([^"']*search\.php[^"']*)["']""", text, re.I):
        raw = m.group(1).replace("&amp;", "&")
        absu = C._forum_redirect(raw) if hasattr(C, "_forum_redirect") else None
        if not absu:
            continue
        if re.search(r"[?&]o=\d+", absu) or re.search(r"[?&]r=", absu):
            found = absu
            if re.search(r"[?&]o=\d+", absu):
                break
    return found


def console_db_path(repo):
    return os.path.join(repo, "tv", "d2jsp_price_db.json")


def wait_if_console_just_asked(repo, gap=CONSOLE_DB_QUIET_S):
    """Stand aside if the live console folded a quote in the last minute (#30 lookups)."""
    path = console_db_path(repo)
    try:
        age = time.time() - os.path.getmtime(path)
    except FileNotFoundError:
        age = None          # no price DB at all: nothing the console wrote can collide with this run
    except OSError as e:
        # REG-3730 (v3899's pre-flight, the swallow ratchet) - an age that will not read is UNKNOWN, never "0 s waited":
        # the console may have written a moment ago, so stand aside the whole gap rather than guess it is quiet
        log("the console's price DB age is UNKNOWN (%s) - standing aside the full %ds" % (type(e).__name__, gap))
        age = 0.0
    if age is None:
        return 0
    if age < gap:
        wait = gap - age
        log("standing aside %.0fs - the console's price DB moved %.0fs ago (not touching it)" % (wait, age))
        time.sleep(wait)
        return wait
    return 0


def decode_page(raw):
    if isinstance(raw, (bytes, bytearray)):
        return raw.decode("utf-8", "replace")
    return str(raw or "")


class FetchLane(object):
    """Read-only signed-in fetch, paced by the caller. Cookie never stored on self in logs."""

    def __init__(self, C, root, urls_path, holder):
        self.C = C
        self.root = root
        self.urls_path = urls_path
        self.holder = holder
        self.urls = read_json(urls_path, {}) or {}
        if not isinstance(self.urls, dict):
            self.urls = {}

    def _remember_url(self, item, url):
        if not url:
            return
        self.urls[item] = url
        write_json(self.urls_path, self.urls)

    def _cookie(self):
        try:
            cookie, reason = self.C.live_cookie_header()
        except Exception:
            cookie, reason = None, "chrome-unread"
        if not cookie:
            self.holder["stop"] = "need-login"
            self.holder["why"] = "sign-in is off (%s)" % (reason or "need-login")
            return None
        return cookie

    def _headers(self, cookie):
        headers = self.C._headers(cookie)
        headers["Referer"] = "https://forums.d2jsp.org/forum.php?f=%d" % self.C.QUOTE_BOARD
        return headers

    def _open_via_chrome(self, kind, arg, cookie):
        """kind is 'search' (item) or 'results' (url). Returns html or None."""
        try:
            if kind == "results":
                return self.C._chrome_open_results(arg, cookie)
            return self.C._chrome_search(arg, cookie)
        except Exception as e:
            # Only our step names, never a message that could hold the page or cookie.
            name = type(e).__name__
            msg = ""
            if isinstance(e, OSError) and e.args and isinstance(e.args[0], str):
                if e.args[0].startswith(("search:", "results:")):
                    msg = e.args[0][:80]
            self.holder["chrome_err"] = msg or name
            return None

    def _finish(self, item, page, results_url=None, cookie=None, tried_chrome=False):
        if results_url:
            self._remember_url(item, results_url)
        need_chrome = cookie is not None and not tried_chrome and (
            is_challenge(page, self.C) or is_hollow_results(page)
        )
        if need_chrome:
            if results_url:
                opened = self._open_via_chrome("results", results_url, cookie)
            else:
                opened = self._open_via_chrome("search", item, cookie)
            tried_chrome = True
            if isinstance(opened, str) and opened:
                if not is_challenge(opened, self.C) and (
                    not is_hollow_results(opened) or is_genuine_empty_results(opened)
                ):
                    page = opened
        if is_challenge(page, self.C) or looks_rate_limited(page):
            why = "rate-limit" if looks_rate_limited(page) else "challenge"
            self.holder["stop"] = "challenge"
            self.holder["why"] = "%s page from d2jsp - no further searches" % why
            self.holder["html"] = None
            return None
        if is_hollow_results(page):
            # Never hand a JS shell to the pager: no Next link would mark the item done.
            self.holder["why"] = "results page had no topics (hollow shell) - will retry"
            self.holder["html"] = None
            return None
        # keep a scrubbed copy locally, never in the repo tree
        try:
            self.C.keep_results_page(item, page, base=os.path.join(self.root, "pages"))
        except Exception:
            pass
        self.holder["html"] = page
        self.holder["last_item"] = item
        return page

    def fetch(self, item, offset):
        self.holder.pop("chrome_err", None)
        self.holder["html"] = None
        cookie = self._cookie()
        if not cookie:
            return NEED_LOGIN_HTML
        transport = self.C._transport
        headers = self._headers(cookie)
        offset = int(offset or 0)
        results_url = self.urls.get(item)

        if offset > 0 and results_url:
            get_headers = dict((k, v) for k, v in headers.items() if k != "Content-Type")
            url = with_offset(results_url, offset)
            try:
                status, hdrs, raw = transport("GET", url, get_headers, None)
            except Exception as e:
                self.holder["why"] = "results GET raised %s" % type(e).__name__
                status, hdrs, raw = None, {}, b""
            page = decode_page(raw)
            if status in (301, 302, 303, 307, 308) and isinstance(hdrs, dict):
                loc = hdrs.get("Location") or hdrs.get("location") or ""
                if "login" in str(loc).lower():
                    self.holder["stop"] = "need-login"
                    self.holder["why"] = "results page redirected to login"
                    return NEED_LOGIN_HTML
            if status == 200 and page and not is_challenge(page, self.C):
                return self._finish(item, page, results_url=results_url, cookie=cookie)
            # fall through: re-run the search, then open o=offset

        # New search (offset 0, or paging without a saved results URL, or a stale URL).
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        status = None
        hdrs = {}
        raw = b""
        err = None
        for _try in (1, 2):
            try:
                status, hdrs, raw = transport("POST", self.C._search_url(item), headers, self.C._search_body(item))
                err = None
                break
            except Exception as e:
                err = type(e).__name__
        if err is not None:
            self.holder["why"] = "search POST raised %s twice" % err
            opened = self._open_via_chrome("search", item, cookie)
            if isinstance(opened, str) and opened:
                return self._finish(item, opened, cookie=cookie, tried_chrome=True)
            self.holder["stop"] = "challenge"
            self.holder["why"] = "search POST failed (%s) and Chrome did not open results" % err
            return None
        results_url = None
        if status in (301, 302, 303, 307, 308):
            loc = ""
            if isinstance(hdrs, dict):
                loc = hdrs.get("Location") or hdrs.get("location") or ""
            if "login" in str(loc).lower():
                self.holder["stop"] = "need-login"
                self.holder["why"] = "search redirected to login"
                return NEED_LOGIN_HTML
            nxt = self.C._forum_redirect(loc)
            if not nxt:
                self.holder["why"] = "search redirected off the forum"
                self.holder["stop"] = "challenge"
                return None
            results_url = nxt
            get_headers = dict((k, v) for k, v in headers.items() if k != "Content-Type")
            try:
                status, hdrs, raw = transport("GET", nxt, get_headers, None)
            except Exception as e:
                self.holder["why"] = "results GET raised %s" % type(e).__name__
                raw = b""
                status = 0
            if status in (301, 302, 303, 307, 308):
                loc2 = (hdrs.get("Location") or hdrs.get("location") or "") if isinstance(hdrs, dict) else ""
                if "login" in str(loc2).lower():
                    self.holder["stop"] = "need-login"
                    self.holder["why"] = "results page redirected to login"
                    return NEED_LOGIN_HTML
        page = decode_page(raw)
        if not results_url:
            results_url = results_url_from_html(page, self.C)
        if offset > 0 and results_url:
            # same search, later page — one paced fetch
            get_headers = dict((k, v) for k, v in headers.items() if k != "Content-Type")
            url = with_offset(results_url, offset)
            try:
                status, hdrs, raw = transport("GET", url, get_headers, None)
                page = decode_page(raw)
            except Exception as e:
                self.holder["why"] = "paged GET raised %s" % type(e).__name__
        return self._finish(item, page, results_url=results_url, cookie=cookie)


def make_parse(C, repo, holder):
    js_path = os.path.join(repo, "functions", "api", "d2jsp_quote.js")

    def parse(html, item, read_at):
        if holder.get("stop") == "need-login":
            return {"reason": "need-login", "item": item, "posts": []}
        if holder.get("stop") == "challenge" or html is None:
            return {"reason": "unread", "item": item, "posts": []}
        text = str(html or "")
        if re.search(r"do not have permission|not currently logged in", text, re.I):
            holder["stop"] = "need-login"
            holder["why"] = "d2jsp answered signed-out / no permission"
            return {"reason": "need-login", "item": item, "posts": []}
        try:
            with open(js_path, encoding="utf-8") as fh:
                src = fh.read()
        except OSError:
            return C.parse_public_quote(html, item, read_at)
        mark = "/* ⟦D2JSP QUOTE BEGIN⟧ */\n"
        try:
            start = src.index(mark) + len(mark)
            end = src.index("\n/* ⟦D2JSP QUOTE END⟧ */", start)
            parser = src[start:end]
        except ValueError:
            return C.parse_public_quote(html, item, read_at)
        since = cutoff_date()
        parser = parser.replace(
            "var D2JSP_QUOTE_WINDOW_DAYS = 120;",
            "var D2JSP_QUOTE_WINDOW_DAYS = 731;",
        )
        parser = parser.replace(
            "var D2JSP_QUOTE_SINCE_MS = Date.UTC(2026, 0, 1);",
            "var D2JSP_QUOTE_SINCE_MS = Date.UTC(%d, %d, %d);" % (since.year, since.month - 1, since.day),
        )
        prog = (
            parser
            + "\nprocess.stdout.write(JSON.stringify(d2jspRead("
            + "require('fs').readFileSync(0,'utf8'),"
            + json.dumps(str(item or "")) + ","
            + json.dumps(str(read_at or ""))
            + ")));\n"
        )
        try:
            node = C._node_bin()
            if not node:
                return C.parse_public_quote(html, item, read_at)
            proc = C._node_run(node, prog, text)
        except Exception:
            return C.parse_public_quote(html, item, read_at)
        if getattr(proc, "returncode", 1) != 0:
            return C.parse_public_quote(html, item, read_at)
        try:
            parsed = json.loads(getattr(proc, "stdout", "") or "")
        except (TypeError, ValueError):
            return C.parse_public_quote(html, item, read_at)
        out = C._public_fields(parsed, item, read_at)
        try:
            import d2jsp_backfill as B
            holder["filled"] = B.fill_authors(out, text)     # REG-3793 - the seller off the results page's own rows
        except Exception:
            holder["filled"] = 0
        try:
            words = C._search_keywords(item)
            if isinstance(words, str) and words.strip():
                out["searched"] = words.strip()[:80]
        except Exception:
            pass
        holder["reading"] = {
            "reason": out.get("reason"),
            "n": out.get("n"),
            "posts": len(out.get("posts") or []),
            "linked": sum(1 for p in (out.get("posts") or []) if p.get("link")),
            "authors": sorted({p.get("author") for p in (out.get("posts") or []) if p.get("author")}),
            "days": sorted({str(p.get("day") or "")[:10] for p in (out.get("posts") or []) if p.get("day")}),
        }
        return out

    return parse


def make_fold(db_path, holder):
    import d2jsp_price_db as P

    def fold(reading):
        db = P.load(db_path)
        if db is None:
            holder["fold_err"] = "price db would not read"
            return 0
        src = "backfill-shard%s" % os.environ.get("D2JSP_BACKFILL_SHARD", "?")
        # REG-3792 - the stored w stays the parser's; one seller / one topic is one vote at price time (vote_shares),
        # so rows are never re-weighted here (the old reweight_sellers rewrote w on every fold)
        added = P.ingest(db, reading, src, key=reading.get("searched") if isinstance(reading, dict) else None)
        P.save(db_path, db)
        return added

    return fold


def mark_done_if_cutoff(progress_path, item, reading_info):
    """Stop paging an item once this page has fallen past the 2-year cutoff."""
    import d2jsp_backfill as B
    import d2jsp_price_db as P

    days = (reading_info or {}).get("days") or []
    if not days:
        return False
    cut = cutoff_date().isoformat()
    # If every dated post on this page is older than the cutoff, we are past the window.
    if all(d < cut for d in days):
        rec = B.progress_load(progress_path)
        if rec is None:
            return False
        st = rec.get("items", {}).get(P.key_of(item))
        if isinstance(st, dict) and not st.get("done"):
            st["done"] = True
            st["why"] = "past 2-year cutoff"
            B.progress_save(progress_path, rec)
            return True
    return False


def summarize_progress(progress_path, db_path, n_queue):
    import d2jsp_backfill as B
    import d2jsp_price_db as P

    rec = B.progress_load(progress_path) or {}
    items = rec.get("items") or {}
    done = sum(1 for st in items.values() if isinstance(st, dict) and st.get("done"))
    pages = sum(int(st.get("pages") or 0) for st in items.values() if isinstance(st, dict))
    folded = sum(int(st.get("folded") or 0) for st in items.values() if isinstance(st, dict))
    pending = n_queue - done
    db = P.load(db_path) if os.path.exists(db_path) else None
    db_items = len((db or {}).get("items") or {}) if isinstance(db, dict) else 0
    db_posts = 0
    if isinstance(db, dict):
        for it in (db.get("items") or {}).values():
            if isinstance(it, dict):
                db_posts += len(it.get("posts") or {})
    return {
        "queued": n_queue,
        "started": len(items),
        "done": done,
        "pending_items": max(0, pending),
        "pages": pages,
        "folded": folded,
        "db_items": db_items,
        "db_posts": db_posts,
        "lastAskAt": rec.get("lastAskAt") or 0,
    }


def run_loop(args, C=None, sleep=None):
    """The paced loop. `C` (the signed-in d2jsp_chrome) and `sleep` are handed in by a law; the CLI passes neither."""
    sleep = sleep or time.sleep
    root, repo = setup_paths(args.root, args.repo)
    os.environ["D2JSP_BACKFILL_SHARD"] = str(args.shard)
    if not args.no_self_log and not os.environ.get("D2JSP_BACKFILL_LOG"):
        os.environ["D2JSP_BACKFILL_LOG"] = os.path.join(root, "backfill.log")
    write_pid(root)

    import d2jsp_backfill as B

    if os.path.exists(challenge_path(root)) and not args.ignore_challenge_file:
        log("CHALLENGE file already present - exiting without asking (look first; nothing is bypassed)")
        return 2
    C = C or import_live_chrome()
    install_bare_rune_search(C)
    st = login_state(C)
    log("shard %d/%d login: state=%s kind=%s ok=%s - %s" % (
        args.shard, args.shards, st["state"], st["kind"], st["ok"], st["why"]))
    if not st["ok"]:
        write_flag(signed_out_path(root), st["why"])
        log("STOP: this PC is not signed in. Nothing was asked.")
        return 3

    catalog = load_catalog_full(root)
    items_all = catalog["items"]
    # Core catalog is sharded by index. Affix priority names are pinned to a shard
    # in items.json (priorityByShard) so adding them cannot flip existing queues.
    by = catalog.get("priorityByShard") or {}
    priority = [str(x).strip() for x in (by.get(str(args.shard)) or by.get(args.shard) or []) if str(x).strip()]
    if not priority:
        priority = [n for i, n in enumerate(catalog.get("priority") or []) if i % args.shards == args.shard]
    core = [n for n in items_all if n not in (catalog.get("priority") or [])]
    queue = shard_items(core, args.shard, args.shards)
    progress_path = os.path.join(root, "progress-shard%d.json" % args.shard)
    db_path = os.path.join(root, "prices-shard%d.json" % args.shard)
    urls_path = os.path.join(root, "results-urls-shard%d.json" % args.shard)
    rec0 = B.progress_load(progress_path)
    if rec0 is None:
        log("STOP: the progress file would not read - nothing is asked (UNKNOWN)")
        return 1
    rec0 = inject_priority(rec0, priority)
    # seed the shard queue, then re-inject so new names sit in the priority slot
    for n in queue:
        if n not in rec0["queue"]:
            rec0["queue"].append(n)
    rec0 = inject_priority(rec0, priority)
    B.progress_save(progress_path, rec0)
    queue = list(rec0["queue"])
    if getattr(args, "refresh", False):
        got = B.queue_monthly_refresh(progress_path, db_path)
        log("monthly refresh: %s - %s" % (got["why"], ",".join(got["queued"][:20]) or "-"))
    holder = {}
    lane = FetchLane(C, root, urls_path, holder)
    parse = make_parse(C, repo, holder)
    fold = make_fold(db_path, holder)

    log("shard %d starting: %d items, priority=%s, progress=%s, db=%s, cutoff=%s, pace=1 search/min" % (
        args.shard, len(queue), ",".join(priority) or "-", os.path.basename(progress_path),
        os.path.basename(db_path), cutoff_date().isoformat()))

    passes = 0
    while True:
        if want_stop(root):
            log("STOP file present - exiting cleanly, progress is saved")
            return 0
        if os.path.exists(challenge_path(root)) and not args.ignore_challenge_file:
            log("CHALLENGE file already present - exiting without asking")
            return 2
        if not args.no_console_wait:
            wait_if_console_just_asked(repo)
        holder.pop("stop", None)
        holder.pop("why", None)
        holder.pop("reading", None)
        out = B.run_once(
            progress_path,
            db_path,
            fetch=lane.fetch,
            parse=parse,
            fold=fold,
            items=queue,
            min_gap_s=SEARCH_GAP_S,
            src="backfill-shard%d" % args.shard,
        )
        passes += 1
        info = holder.get("reading") or {}
        asked = out.get("asked")
        if asked and info.get("days"):
            if mark_done_if_cutoff(progress_path, asked, info):
                out["done"] = True
                out["why"] = (out.get("why") or "") + " - marked done past 2-year cutoff"
        summ = summarize_progress(progress_path, db_path, len(queue))
        log(
            "pass=%d worked=%s asked=%s o=%s folded=%s done=%s posts=%s linked=%s authors=%s days=%s "
            "pages_total=%s folded_total=%s items_done=%s/%s why=%s"
            % (
                passes,
                out.get("worked"),
                asked,
                out.get("offset"),
                out.get("folded"),
                out.get("done"),
                info.get("posts"),
                info.get("linked"),
                ",".join(info.get("authors") or []) or "-",
                ",".join(info.get("days") or []) or "-",
                summ["pages"],
                summ["folded"],
                summ["done"],
                summ["queued"],
                out.get("why") or holder.get("why") or "",
            )
        )
        stop = holder.get("stop")
        if stop == "challenge" or (out.get("worked") and looks_rate_limited(holder.get("html") or "")):
            why = holder.get("why") or out.get("why") or "challenge"
            write_flag(challenge_path(root), why)
            log("CHALLENGE/RATE-LIMIT: %s - stopping this shard" % why)
            return 2
        if stop == "need-login" or (isinstance(holder.get("reading"), dict) and holder["reading"].get("reason") == "need-login") or "sign-in is off" in str(out.get("why") or ""):
            why = holder.get("why") or out.get("why") or "need-login"
            write_flag(signed_out_path(root), why)
            log("SIGNED OUT: %s - stopping this shard, nothing posted" % why)
            return 3
        if out.get("why") == "every queued item is done":
            log("shard %d complete: pages=%s folded=%s db_items=%s db_posts=%s" % (
                args.shard, summ["pages"], summ["folded"], summ["db_items"], summ["db_posts"]))
            return 0
        if args.once and out.get("worked"):
            log("--once: one search finished, exiting (progress saved)")
            return 0
        if args.once and not out.get("worked") and "pace" not in str(out.get("why") or ""):
            log("--once: no search went out (%s) - exiting" % (out.get("why") or "unknown"))
            return 1
        # Honour the 1/min pace (and leftover seconds from run_once).
        rec = __import__("d2jsp_backfill").progress_load(progress_path) or {}
        last = float(rec.get("lastAskAt") or 0)
        now = time.time()
        wait = SEARCH_GAP_S - (now - last) if last else 0
        if wait < 1:
            wait = 1 if not out.get("worked") else SEARCH_GAP_S
        # wake sooner only to notice a STOP file
        end = time.time() + max(1, wait)
        while time.time() < end:
            if want_stop(root):
                log("STOP file present during wait - exiting cleanly")
                return 0
            sleep(min(5, max(1, end - time.time())))


def cmd_status(args):
    root, repo = setup_paths(args.root, args.repo)
    import d2jsp_backfill as B  # noqa: F401

    C = import_live_chrome()
    install_bare_rune_search(C)
    st = login_state(C)
    log("login: state=%s kind=%s ok=%s - %s" % (st["state"], st["kind"], st["ok"], st["why"]))
    items_all = load_catalog(root)
    queue = shard_items(items_all, args.shard, args.shards)
    progress_path = os.path.join(root, "progress-shard%d.json" % args.shard)
    db_path = os.path.join(root, "prices-shard%d.json" % args.shard)
    summ = summarize_progress(progress_path, db_path, len(queue))
    flags = []
    if os.path.exists(stop_path(root)):
        flags.append("STOP")
    if os.path.exists(challenge_path(root)):
        flags.append("CHALLENGE")
    if os.path.exists(signed_out_path(root)):
        flags.append("SIGNED_OUT")
    log("shard %d status: %s flags=%s pidfile=%s" % (
        args.shard, json.dumps(summ, sort_keys=True), ",".join(flags) or "-", pid_path(root)))
    return 0 if st["ok"] else 3


def import_into(root, shard, target, dry_run=False, quiet_s=CONSOLE_DB_QUIET_S):
    """REG-3790 - fold this run folder's prices-shard<N>.json into `target` (the console's price DB). Offline: no sign-in,
    no network. Idempotent (d2jsp_price_db.import_backfill). Refuses while the target moved in the last `quiet_s`
    seconds (the console just folded a quote) and re-reads it right before the write. -> (exit code, stats)"""
    import d2jsp_price_db as P

    src_path = os.path.join(os.path.abspath(root), "prices-shard%d.json" % shard)
    other = P.load(src_path) if os.path.exists(src_path) else None
    if other is None:
        log("IMPORT: %s would not read - nothing imported (UNKNOWN)" % os.path.basename(src_path))
        return 1, None
    try:
        age = time.time() - os.path.getmtime(target)
    except OSError:
        age = None
    if age is not None and age < quiet_s and not dry_run:
        log("IMPORT: the price DB moved %.0fs ago (the console is folding) - try again in a minute" % age)
        return 4, None
    db = P.load(target)
    if db is None:
        log("IMPORT: the price DB would not read - nothing imported over it (UNKNOWN)")
        return 1, None
    stats = P.import_backfill(db, other)
    if dry_run:
        log("IMPORT (dry run, nothing written): %s" % json.dumps(stats, sort_keys=True))
        return 0, stats
    if stats["items"]:
        fresh = P.load(target)
        if fresh is None:
            log("IMPORT: the price DB stopped reading - nothing written (UNKNOWN)")
            return 1, None
        stats = P.import_backfill(fresh, other)      # over the newest bytes, so a quote folded meanwhile is kept
        P.save(target, fresh)
    log("IMPORT: %s" % json.dumps(stats, sort_keys=True))
    return 0, stats


def check_authors(root):
    """REG-3793 - how many topics the kept results pages name a seller for. Reads RUN/pages only; asks nothing."""
    import d2jsp_backfill as B

    d = os.path.join(os.path.abspath(root), "pages")
    pages = sorted(f for f in os.listdir(d) if f.endswith(".html")) if os.path.isdir(d) else []
    named = 0
    for f in pages:
        with open(os.path.join(d, f), encoding="utf-8", errors="replace") as fh:
            n = len(B.topic_authors(fh.read()))
        named += n
        log("authors: %s names %d topic seller(s)" % (f, n))
    log("authors: %d kept page(s), %d topic seller(s) named" % (len(pages), named))
    return 0 if pages else 1


def main(argv=None):
    p = argparse.ArgumentParser(description="Read-only #151 d2jsp backfill")
    p.add_argument("--root", required=True, help="run folder (Desktop/verify-evidence/d2jsp-backfill)")
    p.add_argument("--repo", required=True, help="live console repo (for signed-in d2jsp_chrome only)")
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=SHARDS)
    p.add_argument("--once", action="store_true", help="run at most one search, then exit")
    p.add_argument("--status", action="store_true")
    p.add_argument("--check", action="store_true", help="print sign-in state only, ask nothing")
    p.add_argument("--no-self-log", action="store_true")
    p.add_argument("--ignore-challenge-file", action="store_true")
    p.add_argument("--no-console-wait", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--refresh", action="store_true", help="monthly refresh: re-open only stale items, same pace")
    p.add_argument("--import-into", metavar="DB", help="fold prices-shard<N>.json into this price DB, then exit")
    p.add_argument("--dry-run", action="store_true", help="with --import-into: say what would change, write nothing")
    p.add_argument("--check-authors", action="store_true", help="count sellers the kept pages name, ask nothing")
    args = p.parse_args(argv)
    if args.shard < 0 or args.shard >= args.shards:
        raise SystemExit("shard must be 0..%d" % (args.shards - 1))
    try:
        if args.import_into:
            setup_paths(args.root, args.repo)
            return import_into(args.root, args.shard, os.path.abspath(args.import_into), args.dry_run)[0]
        if args.check_authors:
            setup_paths(args.root, args.repo)
            return check_authors(args.root)
        if args.check or args.status:
            return cmd_status(args)
        return run_loop(args)
    except Exception as e:
        log("runner raised %s - nothing more was asked" % type(e).__name__)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
