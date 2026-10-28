# -*- coding: utf-8 -*-
"""REG-2490 / REG-2491 / REG-2495 / REG-2496 - A d2jsp POST IS SENT ONCE, AND A CLICKED POST IS NEVER CALLED UNSENT.

#106 (Reviewer D), measured at v3784 (7285e7efc):
  - one 25 s deadline in _chrome_post covered loading the board, opening New Trade, filling the
    form, the submit and the redirect. A run that had clicked and had not reached topic.php came
    back as the post.php URL, which _send_through_chrome called 'not-posted', and any OSError after
    the click was 'unread'. Both read "nothing was posted" on the page, so he clicks again and a
    duplicate goes up. _chrome_edit and _send_edit (the shop list's saved topic) had the same shape.
  - the server had no lock. d2jsp_send ran once per request on a ThreadingHTTPServer, so a board
    reload or a second tab started a second Chrome post; only the page's `posting` flag guarded it.
#83: an ImportError of websocket escaped the route, and a Chrome that would not start read 'unread'.
T1 review: the re-send record answered A, B, A on one topic 'already-posted' while the board showed B
(REG-2495); a fill DevTools answered with an error in place of a result read as no click (REG-2496);
and no case here ran the click mark or the edit flow, so deleting either stayed green.

No Chrome runs here. The REAL flow (_chrome_post / _chrome_edit, _run_flow, _flow_step) drives the
REAL desk._Page - so _cdp_call, _SNAPSHOT_JS, _open_link_js and _fill_js are what run - over
DevTools(), a socket whose tab is a Board made of strings, on a clock the flow's own naps move. The
Board answers those expressions the way a page does: each document has its own window, so the mark
the fill script sets is gone on the next document, a form still loading has no button yet, and an
expression it cannot read is recorded and fails the case.
  - two sends at once (threads and an Event): one Chrome post runs; the other is busy, reads no cookie.
  - the form and the receipt have their own budgets: a board that shows the form after 20 s and the
    new topic 25 s after the click is submitted, and the fill never runs on a form still loading.
  - the click mark: the compose page the submit has not left yet is not the form sent back.
  - a click with no receipt is maybe-sent with the board and the time, and so is a browser that stops
    answering once the fill was sent; a fill answered with an error in place of a result is a click.
    The board sending the form back is not-posted, and so is a run that never clicked; unread when no
    forum page ever loaded. The page the click was on is never its own receipt.
  - an edit of the saved topic: the topic is submitted, a click with no receipt is maybe-sent, the
    form sent back or a topic with no Edit link is not-posted, and an edit never opens a new trade.
  - after the receipt wait the board list is read again, once it has loaded: a new topic whose text is
    exactly the subject is the receipt; an older one, listed before the click or bumped in from page 2,
    never is, and two new ones are maybe-sent.
  - the same draft inside 30 minutes of maybe-sent / submitted reads no cookie and starts no Chrome
    (maybe-sent-recently / already-posted); another body, another board, or 30 minutes later, runs.
    A, B, A on one topic runs the third edit, and a record that names no topic never holds back an edit.
  - the urllib seam a law drives (production posts through Chrome) posts once: after its POST a lost
    answer or an unknown page is maybe-sent, and only the form coming back is not-posted.
  - a missing websocket module, a missing Chrome and a Chrome that exits before its DevTools answers
    are chrome-start with a why, and leave no profile and nothing in flight.
  - every answer's reason is one of SEND_REASONS, and none carries the cookie.
RED_PROOF below.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import tempfile
import threading
import types
import unittest
import urllib.parse
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 - this run's scratch dirs leave with it
_fx_tmp.contain()
from console_safe import enable  # noqa: E402
enable()

import d2jsp_chrome as desk  # noqa: E402

ORIGIN = "http://127.0.0.1:17772"
HOST = "127.0.0.1:17772"
PORT = 17772
COOKIE = "sid=SECRETCOOKIE"
SUBJECT = "Selling Grief Phase Blade"
BODY = "Selling Grief Phase Blade\n+340-400% Enhanced Damage\n30 fg"
BOARD_URL = "https://forums.d2jsp.org/forum.php?f=268"
FORM_URL = "https://forums.d2jsp.org/post.php?mode=newtrade&f=268"
SAVED_URL = "https://forums.d2jsp.org/topic.php?t=9001&f=268"      # the shop list's saved topic
EDIT_URL = "https://forums.d2jsp.org/post.php?mode=edit&p=55"     # that topic's own Edit link
T0 = 1800000000.0
# the board before the click: an older topic with this very subject (t=200) and newer ones beside it
LISTED = [(910, "Selling Shako"), (905, "WTB Enigma"), (200, SUBJECT), (880, "Selling Ber")]


class Clock(object):
    """The flow's clock. Its nap moves time on, so no case sleeps."""

    def __init__(self, t=1000.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def nap(self, seconds):
        self.t += float(seconds)


class SocketTimeout(Exception):
    """What websocket-client raises when the browser says nothing in time. Not an OSError."""


class _Anchors(HTMLParser):
    """The <a href> links of a page with their text, read here and not by the module under test."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.links = []
        self._at = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._at = [dict(attrs).get("href") or "", ""]

    def handle_data(self, data):
        if self._at is not None:
            self._at[1] += data

    def handle_endtag(self, tag):
        if tag == "a" and self._at is not None:
            self.links.append((self._at[0], " ".join(self._at[1].split())))
            self._at = None


def _js_string(script, before):
    """The JSON string literal right after `before` in a script, decoded. None when there is none."""
    at = script.find(before)
    if at < 0:
        return None
    try:
        value, _end = json.JSONDecoder().raw_decode(script[at + len(before):])
    except ValueError:
        return None
    return value if isinstance(value, str) else None


def _top_parts(text):
    """text cut at each comma that is not inside quotes or brackets."""
    parts, cur, depth, quote = [], [], 0, None
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


def _tid(url):
    return int(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["t"][0])


class Board(object):
    """Board 268 behind one scratch-Chrome tab, as strings: the topic list with its New Trade link,
    the trade form, the saved topic with its Edit link and the edit form, and what a submit does.

    It is driven through the REAL desk._Page over DevTools(): every snapshot it answers is
    _SNAPSHOT_JS and every act is _open_link_js or _fill_js as the module wrote them. It reads those
    expressions as a page would: a document's window is its own (the mark the fill script sets is
    gone on the next document), a form still loading has no Selling Item radio or button yet, and
    an expression it cannot read goes to self.unknown, which fails the case.

    then: what the submit does - 'topic' (the board lands on the topic land_after seconds after the
    click; until then the clicked document stays on screen), 'stay' (the page never moves on),
    'form' (the board answers with the form again), 'silent' (the browser stops answering once the
    fill was sent; the click still happened) or 'error' (the click navigates at once and DevTools
    answers the fill with "Execution context was destroyed" in place of a result). The board takes
    the post in every case but 'form'; `shown` is what each topic shows."""

    def __init__(self, clock, listed=LISTED, then="stay", listed_after=None, new_id=0,
                 form_after=0.0, land_after=0.0, loads=True, trade_link=True, aside_after=(),
                 edit_link=True, shown=None, list_load_s=0.0):
        self.clock = clock
        self.list_load_s = list_load_s           # the board list read again after the click loads this long
        self.listed = list(listed)
        self.listed_after = listed_after
        self.aside_after = list(aside_after)    # [(topic id, title, board)] a sidebar shows after the click
        self.then = then
        self.new_id = new_id
        self.form_after = form_after             # a form opened from its link is still loading this long
        self.land_after = land_after
        self.loads = loads
        self.trade_link = trade_link
        self.edit_link = edit_link
        self.shown = {} if shown is None else shown
        self.href = "about:blank"
        self.window = {}
        self.ready_at = 0.0
        self.pending = None
        self.gone = False
        self.events = []
        self.opened_at = None
        self.clicked_at = None
        self.gotos = []
        self.ran = []
        self.clicks = 0
        self.sent = []
        self.early_fills = 0
        self.unknown = []

    # -- the tab ---------------------------------------------------------------------------------
    def _commit(self, url, load_s=0.0):
        """A new document: its own window, so no mark, and its own readyState."""
        self.href = url
        self.window = {}
        self.ready_at = self.clock() + load_s
        self.events.append({"method": "Page.frameNavigated", "params": {"frame": {"id": "F1", "url": url}}})

    def _settle(self):
        """The navigation a submit started commits once its time has come."""
        if self.pending is not None and self.clock() >= self.pending[0]:
            url = self.pending[1]
            self.pending = None
            self._commit(url)

    def _ready(self):
        return "complete" if self.clock() >= self.ready_at else "loading"

    def navigate(self, url):
        self.gotos.append((url, self.clock()))
        self.pending = None
        slow = url == BOARD_URL and self.clicked_at is not None
        self._commit(url, load_s=self.list_load_s if slow else 0.0)

    def evaluate(self, expr):
        """Runtime.evaluate. -> ('value', a string or None) or ('error', None)"""
        self._settle()
        if expr.startswith("JSON.stringify({") and expr.endswith("})"):
            return "value", self._snapshot(expr[len("JSON.stringify({"):-len("})")])
        if "document.querySelectorAll('a')" in expr and "label!==" in expr:
            return "value", self._follow(expr)
        if json.dumps('textarea[name="Post"]') in expr:
            return self._fill(expr)
        self.unknown.append(expr[:80])
        return "value", None

    # -- the three expressions -------------------------------------------------------------------
    def _snapshot(self, inner):
        got = {}
        for part in _top_parts(inner):
            key, colon, js = part.partition(":")
            if not colon:
                self.unknown.append(part)
                continue
            got[key.strip()] = self._value(js.strip())
        return json.dumps(got)

    def _value(self, js):
        """One field of the snapshot object, as this page computes it."""
        if js == "location.href":
            return self.href
        if js == "document.readyState":
            return self._ready()
        if js == "document.documentElement?document.documentElement.outerHTML:''":
            return self._html()
        flag = re.fullmatch(r"!!window\.([A-Za-z_$][\w$]*)", js)
        if flag:
            return bool(self.window.get(flag.group(1)))
        if js in ("''", '""'):
            return ""
        if js in ("true", "false"):
            return js == "true"
        self.unknown.append(js)
        return None

    def _follow(self, expr):
        """The link script: follow the link whose text is exactly its label (to post.php when it says so)."""
        label = _js_string(expr, "label!==")
        if label is None:
            self.unknown.append(expr[:80])
            return None
        self.ran.append("open:" + label)
        only_post = "if(href.indexOf('/post.php')<0)continue;" in expr
        links = _Anchors()
        links.feed(self._html())
        links.close()
        for href, text in links.links:
            url = urllib.parse.urljoin(self.href, href)
            if text != label or (only_post and "/post.php" not in url):
                continue
            if url in (FORM_URL, EDIT_URL):
                self.opened_at = self.clock()
                self._commit(url, load_s=self.form_after)
            else:
                self._commit(url)
            return "opened"
        return "no-link"

    def _fill(self, expr):
        """The fill script: on a loaded trade or edit form, fill it and press its submit."""
        self.ran.append("fill")
        if self.href not in (FORM_URL, EDIT_URL):
            return "value", "no-form"
        if self._ready() == "loading":
            self.early_fills += 1               # what has arrived of the form has no radio or button yet
            return "value", "no-sell"
        for need in (json.dumps('textarea[name="Post"]'), json.dumps('input[name="ttitle"]'),
                     "Selling Item", json.dumps('input[name="submit"]'), "btn.click()"):
            if need not in expr:
                return "value", "no-form"
        subject = _js_string(expr, "var subject=")
        text = _js_string(expr, "box.value=")
        if subject is None or text is None:
            self.unknown.append(expr[:80])
            return "value", None
        if "if(subject.length>50)return 'title';" in expr and len(subject) > 50:
            return "value", "title"
        press = expr.index("btn.click()")
        for name in re.findall(r"window\.([A-Za-z_$][\w$]*)=1;", expr[:press]):
            self.window[name] = 1
        self.clicks += 1
        self.clicked_at = self.clock()
        self.sent.append((subject, text))
        landing = SAVED_URL if self.href == EDIT_URL else self._new_topic()
        if self.then != "form":
            self.shown[_tid(landing)] = text
        if self.then == "silent":
            self.gone = True
            return "value", "clicked"
        if self.then == "error":
            self._commit(landing)
            return "error", None
        if self.then in ("topic", "form"):
            self.pending = (self.clicked_at + self.land_after, landing if self.then == "topic" else self.href)
        return "value", "clicked"

    # -- the pages -------------------------------------------------------------------------------
    def _new_topic(self):
        return "https://forums.d2jsp.org/topic.php?t=%d&f=268" % self.new_id

    def _html(self):
        if not self.loads:
            return "<title>Just a moment...</title>"
        if self.href == BOARD_URL:
            rows = self.listed
            if self.clicked_at is not None and self.listed_after is not None:
                rows = self.listed_after
            links = "".join('<tr><td><a href="topic.php?t=%d&amp;f=268">%s</a></td></tr>' % row
                            for row in rows)
            if self.clicked_at is not None:
                links += "".join('<li><a href="topic.php?t=%d&amp;f=%d">%s</a></li>' % (t, f, title)
                                 for t, title, f in self.aside_after)
            trade = '<a href="post.php?mode=newtrade&amp;f=268">New Trade</a>' if self.trade_link else ""
            if self._ready() == "loading":
                links = ""                    # its rows have not arrived yet
            return ('<html><head></head><body><a href="login.php?mode=logout">Log Out</a>%s<table>%s</table>'
                    '</body></html>' % (trade, links))
        if self.href in (FORM_URL, EDIT_URL):
            head = ('<html><head></head><body><form action="post.php"><input name="ttitle">'
                    '<textarea name="Post"></textarea>')
            if self._ready() == "loading":
                return head
            return head + ('<label for="s1">Selling Item</label><input type="radio" id="s1" name="sType">'
                           '<input type="submit" name="submit"></form></body></html>')
        if "topic.php" in self.href:
            edit = '<a href="post.php?mode=edit&amp;p=55">Edit</a>' if self.edit_link else ""
            return "<html><head></head><body><h1>%s</h1>%s</body></html>" % (SUBJECT, edit)
        return "<html><head></head><body></body></html>"


class DevTools(object):
    """The Board's DevTools socket, as desk._Page uses it: send() one call, recv() what comes back,
    the page's events first. A browser that stopped answering sends nothing, and recv() raises."""

    def __init__(self, board):
        self.board = board
        self.inbox = []

    def send(self, raw):
        msg = json.loads(raw)
        board = self.board
        if board.gone:
            return
        method = msg.get("method")
        params = msg.get("params") or {}
        reply = {"id": msg.get("id"), "result": {}}
        if method == "Page.navigate":
            board.navigate(str(params.get("url") or ""))
            reply["result"] = {"frameId": "F1"}
        elif method == "Runtime.evaluate":
            if params.get("returnByValue") is not True:
                board.unknown.append("Runtime.evaluate without returnByValue")
            kind, value = board.evaluate(str(params.get("expression") or ""))
            if board.gone:
                return
            if kind == "error":
                reply = {"id": msg.get("id"),
                         "error": {"code": -32000, "message": "Execution context was destroyed."}}
            elif isinstance(value, str):
                reply["result"] = {"result": {"type": "string", "value": value}}
            else:
                reply["result"] = {"result": {"type": "object", "subtype": "null", "value": None}}
        else:
            board.unknown.append(str(method))
        self.inbox.extend(board.events)
        del board.events[:]
        self.inbox.append(reply)

    def recv(self):
        if not self.inbox:
            raise SocketTimeout("the browser did not answer")
        return json.dumps(self.inbox.pop(0))


class Seat(object):
    """One console posting through the real flow over a Board. Counts its cookie reads and Chrome starts."""

    def __init__(self, board=None, clock=None):
        self.clock = clock or Clock()
        self.board = board
        self.cookies = 0
        self.starts = 0
        self.prefixes = []
        self.posts = 0
        self.edits = 0

    def cookie_get(self):
        self.cookies += 1
        return COOKIE, "ok"

    def chrome(self, cookie, prefix):
        """The scratch Chrome a flow starts: the real _Page over the board's DevTools socket."""
        self.starts += 1
        self.prefixes.append(prefix)
        return contextlib.nullcontext(desk._Page(DevTools(self.board)))

    def chrome_post(self, subject, text, cookie):
        self.posts += 1
        return desk._chrome_post(subject, text, cookie, 268, chrome=self.chrome,
                                 clock=self.clock, nap=self.clock.nap)

    def edit_post(self, topic, subject, text, cookie):
        self.edits += 1
        return desk._chrome_edit(topic, subject, text, cookie, chrome=self.chrome,
                                 clock=self.clock, nap=self.clock.nap)

    def send(self, change=None, now=None):
        draft = {"subject": SUBJECT, "body": BODY, "forum": 268}
        draft.update(change or {})
        return desk.d2jsp_send(draft, ORIGIN, HOST, PORT, cookie_get=self.cookie_get,
                               chrome_post=self.chrome_post, edit_post=self.edit_post,
                               open_login=lambda: False, now=now)


class APostIsSentOnceAndNeverCalledUnsent(unittest.TestCase):

    def setUp(self):
        desk._SENT.clear()
        self.addCleanup(desk._SENT.clear)

    def patch(self, obj, name, value):
        old = getattr(obj, name)
        setattr(obj, name, value)
        self.addCleanup(setattr, obj, name, old)

    def patch_module(self, name, value):
        gone = object()
        old = sys.modules.get(name, gone)
        sys.modules[name] = value

        def restore():
            if old is gone:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
        self.addCleanup(restore)

    def check(self, out):
        """Every answer: one of the declared reasons, and never the cookie."""
        self.assertIn(out.get("reason"), desk.SEND_REASONS, out)
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))
        return out

    def settled(self, board):
        """After any run: the page read every expression, no fill ran on a form still loading, and
        the submit was pressed at most once."""
        self.assertEqual(board.unknown, [], "the page was sent an expression it cannot read")
        self.assertEqual(board.early_fills, 0, "the fill ran on a form that was still loading")
        self.assertLessEqual(board.clicks, 1, "the submit was clicked more than once")

    def post(self, board, clock):
        """The real post flow over `board`. -> its result"""
        seat = Seat(board, clock)
        got = desk._chrome_post(SUBJECT, BODY, COOKIE, 268, chrome=seat.chrome,
                                clock=clock, nap=clock.nap)
        self.assertEqual(seat.prefixes, ["d2jsp-post-"])
        self.settled(board)
        self.assertEqual(board.gotos[0][0], BOARD_URL, "the run did not start on the board list")
        self.assertFalse([u for u, _t in board.gotos if "mode=post" in u], "the old compose address was opened")
        return got

    def edit(self, board, clock):
        """The real edit flow of the saved topic over `board`. -> its result"""
        seat = Seat(board, clock)
        got = desk._chrome_edit(SAVED_URL, SUBJECT, BODY, COOKIE, chrome=seat.chrome,
                                clock=clock, nap=clock.nap)
        self.assertEqual(seat.prefixes, ["d2jsp-post-"])
        self.settled(board)
        self.assertEqual(board.gotos[0][0], SAVED_URL, "the edit did not start on the saved topic")
        self.assertNotIn("open:New Trade", board.ran, "an edit opened a new trade")
        return got

    def verdict(self, got, board=268):
        code, out = desk._send_verdict(got, board, desk._stamp(T0), lambda: False)
        self.assertEqual(code, 200)
        return self.check(out)

    def test_two_sends_at_once_start_one_chrome_post(self):
        inside = threading.Event()
        release = threading.Event()
        count = {"chrome": 0, "cookie": 0}
        guard = threading.Lock()

        def cookie_get():
            with guard:
                count["cookie"] += 1
            return COOKIE, "ok"

        def chrome_post(subject, text, cookie):
            with guard:
                count["chrome"] += 1
                n = count["chrome"]
            if n == 1:
                inside.set()
                release.wait(10)
            return "https://forums.d2jsp.org/topic.php?t=%d&f=268" % (800 + n)

        def send(subject):
            draft = {"subject": subject, "body": subject + "\n30 fg", "forum": 268}
            return desk.d2jsp_send(draft, ORIGIN, HOST, PORT, cookie_get=cookie_get,
                                   chrome_post=chrome_post, open_login=lambda: False)

        got = {}

        def first_send():
            try:
                got["first"] = send("Selling Grief Phase Blade")
            except BaseException as exc:          # a lock released twice raises here
                got["error"] = repr(exc)

        th = threading.Thread(target=first_send, daemon=True)
        th.start()
        try:
            self.assertTrue(inside.wait(10), "the first send never reached Chrome - UNKNOWN, not a pass")
            # another draft, so 'busy' can only come from the lock and never from the re-send record
            code, second = send("Selling Shako Harlequin Crest")
        finally:
            release.set()
            th.join(10)
        self.assertEqual(code, 200)
        self.check(second)
        self.assertEqual(second["reason"], "busy", "a second send ran while one was in flight")
        self.assertFalse(second["ok"])
        self.assertEqual(count["chrome"], 1, "two sends at once started %d Chrome posts" % count["chrome"])
        self.assertEqual(count["cookie"], 1, "a busy send read the cookie")
        self.assertNotIn("error", got)
        self.assertEqual(self.check(got["first"][1])["reason"], "submitted")
        code, third = send("Selling Shako Harlequin Crest")
        self.assertEqual(self.check(third)["reason"], "submitted", "the console stayed busy after the send")
        self.assertEqual(count["chrome"], 2)

    def test_a_slow_board_that_takes_the_post_is_submitted(self):
        # The form is still loading for 20 s and the topic loads 25 s after the click: 46 s in all.
        # One 25 s deadline for both called this post unsent. The fill waits for the loaded form.
        clock = Clock()
        board = Board(clock, then="topic", new_id=951, form_after=20.0, land_after=25.0)
        got = self.post(board, clock)
        out = self.verdict(got)
        self.assertTrue(out["ok"])
        self.assertEqual(out["reason"], "submitted")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=951&f=268")
        self.assertEqual(board.clicks, 1)
        self.assertGreaterEqual(board.clicked_at - board.opened_at, 20.0)
        self.assertEqual(board.sent, [(SUBJECT, BODY)])

    def test_the_click_mark_tells_the_page_the_click_left_from_the_form_sent_back(self):
        # The T1 review's probe: the submit takes 3 s to leave post.php, and the board takes the post.
        # Right after the click the compose document is still on screen. The mark the fill script set
        # on it is the only thing that says it is not the form coming back; without it this read
        # not-posted, the REG-2490 lie.
        clock = Clock()
        board = Board(clock, then="topic", new_id=951, land_after=3.0)
        got = self.post(board, clock)
        out = self.verdict(got)
        self.assertEqual(out["reason"], "submitted", "the page the click had not left yet read as the form sent back")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=951&f=268")

        # the same through the page itself: the fill script sets the mark, the snapshot script reads
        # it back, and the next document starts without it
        clock = Clock()
        board = Board(clock, then="stay")
        page = desk._Page(DevTools(board))
        page.goto(BOARD_URL)
        self.assertEqual(page.act("open-trade", desk._open_link_js("New Trade")), "opened")
        self.assertFalse(page.snapshot()["mark"])
        self.assertEqual(page.act("fill", desk._fill_js(SUBJECT, BODY)), "clicked")
        snap = page.snapshot()
        self.assertEqual((snap["href"], snap["ready"], snap["mark"]), (FORM_URL, "complete", True),
                         "the snapshot does not read back the mark the fill script set")
        page.goto(BOARD_URL)
        self.assertFalse(page.snapshot()["mark"], "a new document carried the mark of the one before")
        self.settled(board)

    def test_a_click_with_no_receipt_is_maybe_sent_never_unsent(self):
        clock = Clock()
        board = Board(clock, then="stay")
        got = self.post(board, clock)
        self.assertTrue(got["clicked"])
        out = self.verdict(got)
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "maybe-sent")
        self.assertEqual(out["board"], 268)
        self.assertEqual(out["at"], desk._stamp(T0))
        self.assertNotIn("topic", out)
        self.assertEqual(board.clicks, 1)
        # the receipt was waited for at least 30 s after the click, and the board list read again
        reread = [t for u, t in board.gotos[1:] if u == BOARD_URL]
        self.assertTrue(reread, "the board list was not read again before maybe-sent")
        self.assertGreaterEqual(reread[0] - board.clicked_at, 30.0)

        clock = Clock()
        board = Board(clock, then="silent")
        got = self.post(board, clock)
        out = self.verdict(got)
        self.assertEqual(out["reason"], "maybe-sent",
                         "a fill that was sent and never answered may have clicked")
        self.assertEqual(board.clicks, 1, "an unanswered submit was sent again")

        # the same through d2jsp_send: the answer carries the time the send began
        clock = Clock()
        seat = Seat(Board(clock, then="stay"), clock)
        code, out = seat.send(now=T0)
        self.check(out)
        self.assertEqual(out["reason"], "maybe-sent")
        self.assertEqual(out["at"], desk._stamp(T0))

    def test_a_fill_answered_with_an_error_in_place_of_a_result_is_a_click(self):
        # REG-2496: the click navigates at once and DevTools answers the fill's evaluate with
        # "Execution context was destroyed" - an error, no result. _Page.act read that as '' (no
        # click), and a post the board took ran out its form budget as form-unknown.
        clock = Clock()
        board = Board(clock, then="error", new_id=952)
        got = self.post(board, clock)
        self.assertTrue(got["clicked"], "a fill answered with an error was read as no click")
        out = self.verdict(got)
        self.assertEqual(out["reason"], "submitted")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=952&f=268")
        self.assertEqual(board.clicks, 1)

    def test_an_edit_that_clicked_is_never_called_unsent(self):
        # REG-2490's edit half (_chrome_edit, _send_edit): the shop list edits its saved topic through
        # the topic's own Edit link, and an edit with no receipt used to read not-posted.
        for then, want in (("topic", "submitted"),     # the board lands back on the topic
                           ("error", "submitted"),     # an error in place of the fill's answer, then the topic
                           ("stay", "maybe-sent"),     # clicked, and the page never moved on
                           ("silent", "maybe-sent"),   # clicked, and the browser stopped answering
                           ("form", "not-posted")):    # the board sent the edit form back
            clock = Clock()
            board = Board(clock, then=then)
            got = self.edit(board, clock)
            out = self.verdict(got)
            self.assertEqual(out["reason"], want, "an edit that went '%s'" % then)
            self.assertEqual(board.clicks, 1, then)
            self.assertEqual(board.sent, [(SUBJECT, BODY)], then)
            if want == "submitted":
                self.assertEqual(out["topic"], SAVED_URL)
            if want == "maybe-sent":
                self.assertEqual((out["board"], out["at"]), (268, desk._stamp(T0)))
                self.assertNotIn("topic", out)

        # a topic with no Edit link is never posted to: nothing is clicked and no new trade starts
        clock = Clock()
        board = Board(clock, edit_link=False)
        got = self.edit(board, clock)
        self.assertFalse(got["clicked"])
        self.assertEqual(board.clicks, 0)
        self.assertEqual(self.verdict(got)["reason"], "not-posted")

        # through d2jsp_send with the saved topic: the edit runs, never a new trade, and a click with
        # no receipt is maybe-sent with the board it was for
        for forum, topic in ((268, SAVED_URL), (271, "https://forums.d2jsp.org/topic.php?t=9002&f=271")):
            clock = Clock()
            seat = Seat(Board(clock, then="stay"), clock)
            code, out = seat.send({"topic": topic, "forum": forum}, now=T0)
            self.check(out)
            self.assertEqual(out["reason"], "maybe-sent", "an edit through d2jsp_send that clicked with no receipt")
            self.assertEqual((out["board"], out["at"]), (forum, desk._stamp(T0)))
            self.assertEqual((seat.edits, seat.posts), (1, 0), "a saved topic started a new trade")
            self.assertEqual(seat.board.gotos[0][0], topic)

        desk._SENT.clear()          # the maybe-sent above holds this very draft on this very topic
        clock = Clock()
        seat = Seat(Board(clock, then="topic"), clock)
        code, out = seat.send({"topic": SAVED_URL}, now=T0)
        self.assertEqual(self.check(out)["reason"], "submitted")
        self.assertEqual(out["topic"], SAVED_URL)

    def test_only_a_run_that_never_clicked_is_unsent(self):
        clock = Clock()
        board = Board(clock, then="form")
        got = self.post(board, clock)
        self.assertTrue(got["clicked"])
        self.assertTrue(got["back"])
        self.assertEqual(self.verdict(got)["reason"], "not-posted",
                         "the board sent the form back and showed no new topic")

        clock = Clock()
        board = Board(clock, trade_link=False)
        got = self.post(board, clock)
        self.assertFalse(got["clicked"])
        self.assertEqual(board.clicks, 0)
        self.assertEqual(self.verdict(got)["reason"], "not-posted")

        clock = Clock()
        board = Board(clock, loads=False)
        got = self.post(board, clock)
        self.assertFalse(got["clicked"])
        self.assertEqual(self.verdict(got)["reason"], "unread")

        clock = Clock()
        board = Board(clock, form_after=60.0)
        got = self.post(board, clock)
        self.assertFalse(got["clicked"])
        self.assertEqual(self.verdict(got)["reason"], "not-posted")

        # a topic page before any click is not a receipt
        st = desk._flow_begin("post", SUBJECT, 268, BOARD_URL)
        st, act = desk._flow_step(st, {"href": "https://forums.d2jsp.org/topic.php?t=9&f=268",
                                       "ready": "complete", "mark": False,
                                       "html": "<html><body>a topic</body></html>"}, 0.0)
        self.assertEqual(act, ("wait",))
        self.assertFalse(st["clicked"])
        # and the page the click was on (it carries the mark) is never its own receipt, topic page or not
        st = desk._flow_begin("edit", SUBJECT, 268, SAVED_URL)
        st.update(phase="receipt", t0=0.0, clicked=True, click_at=0.0)
        st, act = desk._flow_step(st, {"href": SAVED_URL, "ready": "complete", "mark": True,
                                       "html": "<html><body>the topic the click was on</body></html>"}, 1.0)
        self.assertEqual(act, ("wait",), "the page the click was on was taken as its own receipt")

    def test_a_new_same_subject_topic_on_the_board_is_the_receipt(self):
        clock = Clock()
        board = Board(clock, then="stay", listed_after=[(960, SUBJECT)] + LISTED)
        got = self.post(board, clock)
        out = self.verdict(got)
        self.assertTrue(out["ok"])
        self.assertEqual(out["reason"], "submitted")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=960&f=268")

        # the board list read again takes 5 s to load: its rows are waited for, never read half-loaded
        clock = Clock()
        board = Board(clock, then="stay", listed_after=[(960, SUBJECT)] + LISTED, list_load_s=5.0)
        got = self.post(board, clock)
        out = self.verdict(got)
        self.assertEqual(out["reason"], "submitted", "a board list still loading was read as the board")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=960&f=268")

        clock = Clock()
        board = Board(clock, then="stay", listed_after=[(961, SUBJECT), (960, SUBJECT)] + LISTED)
        got = self.post(board, clock)
        self.assertEqual(self.verdict(got)["reason"], "maybe-sent",
                         "two new topics carry the subject: which one is his is unknown")

    def test_an_older_same_subject_topic_is_never_the_receipt(self):
        # t=200 carries the subject and was on the list before the click: not his new post.
        clock = Clock()
        board = Board(clock, then="stay", listed_after=LISTED)
        got = self.post(board, clock)
        out = self.verdict(got)
        self.assertEqual(out["reason"], "maybe-sent", "a topic listed before the click was taken as the receipt")
        self.assertNotIn("topic", out)

        # t=640 was not on the list before the click (bumped in from page 2), and it is older than
        # the newest topic the list showed then (910): not his new post either.
        others = [row for row in LISTED if row[1] != SUBJECT]
        clock = Clock()
        board = Board(clock, listed=others, then="stay", listed_after=[(640, SUBJECT)] + others)
        got = self.post(board, clock)
        out = self.verdict(got)
        self.assertEqual(out["reason"], "maybe-sent", "an older topic bumped onto the list was taken as the receipt")
        self.assertNotIn("topic", out)

        clock = Clock()
        board = Board(clock, listed=others, then="form", listed_after=[(640, SUBJECT)] + others)
        got = self.post(board, clock)
        self.assertEqual(self.verdict(got)["reason"], "not-posted")

        # a new topic with this very title on ANOTHER board (a sidebar link to board 271) is not his post
        clock = Clock()
        board = Board(clock, then="stay", aside_after=[(990, SUBJECT, 271)])
        got = self.post(board, clock)
        out = self.verdict(got)
        self.assertEqual(out["reason"], "maybe-sent", "a same-title topic on another board was taken as the receipt")
        self.assertNotIn("topic", out)

    def test_an_identical_resend_inside_30_minutes_starts_no_chrome(self):
        clock = Clock()
        seat = Seat(Board(clock, then="stay"), clock)
        code, out = seat.send(now=T0)
        self.assertEqual(self.check(out)["reason"], "maybe-sent")
        self.assertEqual((seat.starts, seat.cookies), (1, 1))

        seat.board = Board(clock, then="topic", new_id=970)
        code, out = seat.send(now=T0 + 29 * 60)
        self.check(out)
        self.assertEqual(out["reason"], "maybe-sent-recently")
        self.assertEqual(out["at"], desk._stamp(T0))
        self.assertEqual((seat.starts, seat.cookies), (1, 1), "a re-send inside 30 min started Chrome")

        code, out = seat.send({"body": BODY.replace("30 fg", "35 fg")}, now=T0 + 29 * 60)
        self.assertEqual(self.check(out)["reason"], "submitted", "another body is another draft")
        self.assertEqual(seat.starts, 2)

        seat.board = Board(clock, then="topic", new_id=971)
        code, out = seat.send(now=T0 + 31 * 60)
        self.assertEqual(self.check(out)["reason"], "submitted", "30 minutes on, the same draft runs")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=971&f=268")
        self.assertEqual(seat.starts, 3)

        code, out = seat.send(now=T0 + 45 * 60)
        self.check(out)
        self.assertEqual(out["reason"], "already-posted")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=971&f=268")
        self.assertEqual(out["at"], desk._stamp(T0 + 31 * 60))
        self.assertEqual((seat.starts, seat.cookies), (3, 3), "a re-send after a submit started Chrome")
        # the record is per board: the same draft for board 271 is another draft
        self.assertIsNone(desk._sent_before(desk._sent_key(271, SUBJECT, BODY), T0 + 45 * 60),
                          "a board 268 post answered for the same draft on board 271")

    def test_a_topic_changed_since_is_edited_again(self):
        # REG-2495 (A, B, A): a shop list posted as A, edited to B (an item sold), then edited back to
        # A inside 30 minutes. The record was keyed on the draft alone, so the third send answered
        # already-posted with A's old receipt: the edit never ran, and the board still showed B.
        a_body, b_body = BODY, BODY.replace("30 fg", "45 fg")
        for second in ("topic", "stay"):          # B went up, or may have
            desk._SENT.clear()
            clock = Clock()
            shown = {}
            seat = Seat(Board(clock, then="topic", new_id=9001, shown=shown), clock)
            code, out = seat.send(now=T0)
            self.assertEqual(self.check(out)["reason"], "submitted")
            self.assertEqual(out["topic"], SAVED_URL)
            seat.board = Board(clock, then=second, shown=shown)
            code, out = seat.send({"body": b_body, "topic": SAVED_URL}, now=T0 + 300)
            self.assertIn(self.check(out)["reason"], ("submitted", "maybe-sent"))
            self.assertEqual(shown[9001], b_body)
            seat.board = Board(clock, then="topic", shown=shown)
            code, out = seat.send({"topic": SAVED_URL}, now=T0 + 600)
            self.assertEqual(self.check(out)["reason"], "submitted",
                             "the topic showed B (%s) and the desk answered for A" % second)
            self.assertEqual(seat.edits, 2, "the edit back to A never ran")
            self.assertEqual(shown[9001], a_body)
            # nothing changed the topic since: the identical edit is already-posted and starts no Chrome
            starts = seat.starts
            code, out = seat.send({"topic": SAVED_URL}, now=T0 + 660)
            self.assertEqual(self.check(out)["reason"], "already-posted")
            self.assertEqual((out["topic"], out["at"]), (SAVED_URL, desk._stamp(T0 + 600)))
            self.assertEqual(seat.starts, starts, "an identical re-send started Chrome")

        # a maybe-sent new post holds the same draft back from a second new post, but its record names
        # no topic, so it never answers for an edit of one: an edit cannot make a second topic
        desk._SENT.clear()
        clock = Clock()
        seat = Seat(Board(clock, then="stay"), clock)
        code, out = seat.send(now=T0)
        self.assertEqual(self.check(out)["reason"], "maybe-sent")
        code, out = seat.send(now=T0 + 60)
        self.assertEqual(self.check(out)["reason"], "maybe-sent-recently")
        self.assertEqual(seat.starts, 1)
        seat.board = Board(clock, then="topic")
        code, out = seat.send({"topic": SAVED_URL}, now=T0 + 120)
        self.assertEqual(self.check(out)["reason"], "submitted",
                         "an edit of the saved topic was held back by a record of no topic")
        self.assertEqual(out["topic"], SAVED_URL)
        self.assertEqual(seat.edits, 1)

    def test_the_urllib_seam_never_posts_twice(self):
        # Laws drive d2jsp_send through `transport` (production always posts through Chrome). Its POST
        # is its click: once it went out, a lost answer or a page that is not the form is maybe-sent,
        # and the draft is never posted a second time.
        form = ('<html><body><a href="login.php?mode=logout">Log Out</a><form><input name="subject">'
                '<textarea name="message"></textarea><input type="submit" name="post" value="Post">'
                '</form></body></html>').encode("utf-8")

        def send(answer):
            posts = []

            def transport(method, url, headers, data):
                if method == "GET":
                    return 200, {}, form
                posts.append(data)
                if isinstance(answer, Exception):
                    raise answer
                return answer
            desk._SENT.clear()
            code, out = desk.d2jsp_send({"subject": SUBJECT, "body": BODY, "forum": 268}, ORIGIN, HOST,
                                        PORT, cookie_get=lambda: (COOKIE, "ok"), transport=transport,
                                        chrome_post=False, open_login=lambda: False, now=T0)
            self.assertEqual(len(posts), 1, "the urllib seam posted %d times" % len(posts))
            return self.check(out)

        out = send(OSError("the answer was lost"))
        self.assertEqual(out["reason"], "maybe-sent", "a POST whose answer was lost read as unsent")
        self.assertEqual((out["board"], out["at"]), (268, desk._stamp(T0)))
        out = send((302, {"Location": "topic.php?t=77&f=268"}, b""))
        self.assertEqual(out["reason"], "submitted")
        self.assertEqual(out["topic"], "https://forums.d2jsp.org/topic.php?t=77&f=268")
        self.assertEqual(send((200, {}, b"<title>Just a moment...</title>"))["reason"], "maybe-sent")
        self.assertEqual(send((200, {}, form))["reason"], "not-posted", "the board sent the form back")

    def test_a_chrome_that_cannot_start_is_chrome_start(self):
        made = []
        real_mkdtemp = tempfile.mkdtemp

        def mkdtemp(*args, **kwargs):
            path = real_mkdtemp(*args, **kwargs)
            made.append(path)
            return path
        self.patch(desk, "tempfile", types.SimpleNamespace(mkdtemp=mkdtemp, gettempdir=tempfile.gettempdir))
        swept = []
        self.patch(desk, "_sweep_stale_scratch", lambda now=None, tmp=None: swept.append(1) or 0)
        asked = []

        def no_chrome():
            asked.append(1)
            return None
        self.patch(desk, "_chrome_bin", no_chrome)

        def send():
            code, out = desk.d2jsp_send({"subject": SUBJECT, "body": BODY, "forum": 268},
                                        ORIGIN, HOST, PORT, cookie_get=lambda: (COOKIE, "ok"),
                                        open_login=lambda: False)
            self.assertEqual(code, 200)
            return self.check(out)

        self.patch_module("websocket", None)          # `import websocket` raises ImportError
        out = send()
        self.assertEqual(out["reason"], "chrome-start")
        self.assertEqual(out["why"], desk._START_WHY["websocket"])
        self.assertEqual((asked, made), ([], []), "a run without its websocket module went on to start Chrome")

        self.patch_module("websocket", types.ModuleType("websocket"))
        out = send()
        self.assertEqual(out["reason"], "chrome-start")
        self.assertEqual(out["why"], desk._START_WHY["no-chrome"])
        self.assertEqual(made, [])

        # a "browser" that exits on Chrome's flags: its DevTools never answers
        self.patch(desk, "_chrome_bin", lambda: sys.executable)
        held = []
        real_up = desk._devtools_up

        def devtools_up(base, proc, wait_s=12):
            held.append([pair[0] for pair in desk._IN_FLIGHT.values()] == [proc])
            return real_up(base, proc, wait_s)
        self.patch(desk, "_devtools_up", devtools_up)
        out = send()
        self.assertEqual(out["reason"], "chrome-start")
        self.assertEqual(out["why"], desk._START_WHY["devtools"])
        self.assertEqual(held, [True], "a starting Chrome was not held for the exit reaper")
        self.assertEqual(len(made), 1)
        self.assertTrue(os.path.basename(made[0]).startswith("d2jsp-post-"))
        self.assertFalse(os.path.exists(made[0]), "a Chrome that did not start left its profile")
        self.assertEqual(desk._IN_FLIGHT, {}, "a Chrome that did not start is still held as in flight")
        self.assertEqual(swept, [1], "the scratch Chrome was started without a sweep first")


RED_PROOF = [
    {
        "why": "REG-2490 - the send lock is not taken: a second send while one runs reads the cookie and "
               "starts a second Chrome post",
        "file": "tv/d2jsp_chrome.py",
        "find": '    if not _SEND_LOCK.acquire(False):\n        return 200, {"ok": False, "reason": "busy"}\n',
        "replace": "    _SEND_LOCK.acquire(False)\n",
        "matches": 1,
    },
    {
        "why": "REG-2490 - a clicked submit with no receipt is mapped back to not-posted, the 'nothing was "
               "posted' that invites a duplicate",
        "file": "tv/d2jsp_chrome.py",
        "find": '        return answer({"ok": False, "reason": "maybe-sent", "board": int(board), "at": at})\n',
        "replace": '        return answer({"ok": False, "reason": "not-posted"})\n',
        "matches": 1,
    },
    {
        "why": "REG-2490 - any same-subject topic on the board is taken as the receipt, so an older topic "
               "reads as his new post",
        "file": "tv/d2jsp_chrome.py",
        "find": '                         if tid not in before and st["top"] is not None and tid > st["top"])\n',
        "replace": "                         if True)\n",
        "matches": 1,
    },
    {
        "why": "REG-2490 - a same-title topic on another board (a sidebar link) is taken as the receipt",
        "file": "tv/d2jsp_chrome.py",
        "find": "        if board is not None and fid is not None and fid != int(board):\n            continue\n",
        "replace": "        pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2490 - an identical re-send after a maybe-sent starts Chrome again: a second post of the "
               "same draft",
        "file": "tv/d2jsp_chrome.py",
        "find": '    return {"ok": False, "reason": "maybe-sent-recently", "at": prior["at"]}\n',
        "replace": "    return None\n",
        "matches": 1,
    },
    {
        "why": "REG-2490 - the receipt is given less than 30 s again, so a slow board that took the post "
               "reads as not confirmed",
        "file": "tv/d2jsp_chrome.py",
        "find": "_RECEIPT_S = 35.0",
        "replace": "_RECEIPT_S = 5.0",
        "matches": 1,
    },
    {
        "why": "REG-2490 - a fill that was sent and never answered is read as no click, so the submit is "
               "sent again and the run is called unsent",
        "file": "tv/d2jsp_chrome.py",
        "find": '        if word in ("clicked", _NO_ANSWER):\n',
        "replace": '        if word == "clicked":\n',
        "matches": 1,
    },
    {
        "why": "REG-2491 - a missing websocket module escapes as ImportError again instead of chrome-start",
        "file": "tv/d2jsp_chrome.py",
        "find": '        raise ChromeStart("websocket")\n',
        "replace": "        raise\n",
        "matches": 1,
    },
    {
        "why": "REG-2491 - a Chrome that could not start collapses into unread again",
        "file": "tv/d2jsp_chrome.py",
        "find": '        return None, {"ok": False, "reason": "chrome-start", "why": stop.why}\n',
        "replace": '        return None, {"ok": False, "reason": "unread"}\n',
        "matches": 1,
    },
    {
        "why": "REG-2490 (T1 review) - the fill script no longer marks the page before its click, so the "
               "compose page a slow submit has not left yet reads as the form sent back: not-posted",
        "file": "tv/d2jsp_chrome.py",
        "find": "window.__d2jspClicked=1;btn.click();",
        "replace": "btn.click();",
        "matches": 1,
    },
    {
        "why": "REG-2490 (T1 review) - the snapshot script never reports the click mark, so every document "
               "after the click reads as new and the page the click has not left is the form sent back",
        "file": "tv/d2jsp_chrome.py",
        "find": '    "mark:!!window.__d2jspClicked,"\n',
        "replace": '    "mark:false,"\n',
        "matches": 1,
    },
    {
        "why": "REG-2490 (T1 review) - the snapshot script reports every page loaded, so the fill runs on a "
               "form whose button has not arrived",
        "file": "tv/d2jsp_chrome.py",
        "find": '"JSON.stringify({href:location.href,ready:document.readyState,"',
        "replace": "\"JSON.stringify({href:location.href,ready:'complete',\"",
        "matches": 1,
    },
    {
        "why": "REG-2496 - a DevTools error in place of the fill's result reads as an empty answer, no click, "
               "and a post the board took ends form-unknown",
        "file": "tv/d2jsp_chrome.py",
        "find": '        if not isinstance(got.get("result"), dict):\n            raise _ErrorReply(str(name))\n'
                '        res = got["result"]\n',
        "replace": '        res = got.get("result") or {}\n',
        "matches": 1,
    },
    {
        "why": "REG-2490 (T1 review) - _send_edit goes back to its old shape: an edit with no topic receipt "
               "is not-posted, so a shop-list edit that may have gone through reads as not updated",
        "file": "tv/d2jsp_chrome.py",
        "find": "    return _send_verdict(got, _post_board(forum) or BOARD, at, open_login)\n",
        "replace": '    res = _as_result(got)\n'
                   '    if _public_topic(res["topic"]):\n'
                   '        return 200, {"ok": True, "reason": "submitted", "topic": _public_topic(res["topic"])}\n'
                   '    return 200, {"ok": False, "reason": "not-posted"}\n',
        "matches": 1,
    },
    {
        "why": "REG-2490 (T1 review) - an edit that clicked and saw no receipt is carried out as no click",
        "file": "tv/d2jsp_chrome.py",
        "find": '        if st["kind"] != "post":\n            return _flow_done(st, why=',
        "replace": '        if st["kind"] != "post":\n            st["clicked"] = False\n            return _flow_done(st, why=',
        "matches": 1,
    },
    {
        "why": "REG-2495 - a send that changed a topic leaves the other drafts' records on it, so A, B, A "
               "answers already-posted while the board shows B",
        "file": "tv/d2jsp_chrome.py",
        "find": '    for gone in [k for k, v in _SENT.items() if k != key and v["on"] & on]:\n'
                "        del _SENT[gone]\n",
        "replace": "    pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2495 - an edit is answered by a record of another topic, or of none, so the saved topic "
               "is never edited after a maybe-sent new post",
        "file": "tv/d2jsp_chrome.py",
        "find": '    if ref is not None and ref not in prior["on"]:\n        return None\n',
        "replace": "    pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2490 (T1 review) - the board list read again after the click gets no time to load, so "
               "a post the board lists reads maybe-sent",
        "file": "tv/d2jsp_chrome.py",
        "find": "_CHECK_S = 20.0",
        "replace": "_CHECK_S = 0.0",
        "matches": 1,
    },
    {
        "why": "REG-2490 (T1 review) - the page the click was on is taken as its own receipt when it is a "
               "topic page",
        "file": "tv/d2jsp_chrome.py",
        "find": "        if fresh and readable and _topic(href):\n",
        "replace": "        if readable and _topic(href):\n",
        "matches": 1,
    },
    {
        "why": "REG-2490 (T1 review) - the re-send record ignores the board, so a board 268 post answers for "
               "the same draft on board 271",
        "file": "tv/d2jsp_chrome.py",
        "find": '    return (int(board), str(subject), hashlib.sha256(str(text).encode("utf-8")).hexdigest())\n',
        "replace": '    return (0, str(subject), hashlib.sha256(str(text).encode("utf-8")).hexdigest())\n',
        "matches": 1,
    },
    {
        "why": "REG-2490 (T1 review) - the urllib seam reads a POST whose answer was lost as unread, "
               "'nothing was posted'",
        "file": "tv/d2jsp_chrome.py",
        "find": '        return _send_verdict({"clicked": True}, forum, at, open_login)\n',
        "replace": '        return 200, {"ok": False, "reason": "unread"}\n',
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
