# -*- coding: utf-8 -*-
"""v3864 (his ask 2026-11-05, card 57) - THE TASK BOARD ONLINE, SCRUBBED, ONE CLICK FROM EVERY CONSOLE.

His words: "a link button designed to route me to ... open up as a browser in chrome or whatever is defaulted on that PC" and
"i want it to work on deans PC for instance". The board lives on his Mac (~/.claude/tasks), drawn by a viewer no other PC can
reach. Now:
  * his Mac's console (darwin, an approver label, not suppressed) publishes the board through the roster worker it already
    signs with, as kind "tasks" - at most every 2 min when it changes, every 30 min when it does not;
  * every text is SCRUBBED first (tv/task_board.py): the site password is in this public repo, so no home path, temp path,
    IP, e-mail, user@host, .local host or token-shaped string leaves the Mac;
  * the worker keeps one record, takes it only from an APPROVER's registered key, refuses a write under a minute after the
    last, and hands it at GET /api/roster?tasks=1;
  * /d2r/tasks.html (shipped by deploy.sh) draws it with textContent, never markup, and says how old it is;
  * every console's footer has "Future" (his name for it, 2026-11-05) beside "history": POST /api/open_tasks opens that ONE page in the PC's default
    browser, behind the same origin gate as the d2jsp doors.
Fixtures only, in temp dirs; nothing reaches the site. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import task_board as TB  # noqa: E402
import control_app as CA  # noqa: E402

ROOT = os.path.dirname(HERE)
T0 = 1793900000000
# every machine, person and path here is a stand-in, and the home path and token shape are built at run time: this file is
# public, so it may hold none of them literally (test_no_new_home_path_is_published counts /Users/<name>/)
DIRTY = ("see " + "/" + "Users/someone/d2r_bible_tests/tv/x.py and /private/tmp/claude-v3864/tv on 192.0.2.7, "
         "ssh player@192.0.2.7 or player@host-b, mail someone@example.com, host host-a.local, "
         "C:\\Users\\Player\\AppData and " + "gh" + "p_" + "0" * 36)


def _card(i, st, subject, desc=""):
    return {"id": str(i), "subject": subject, "status": st, "activeForm": "doing " + subject, "description": desc}


class TheBoardIsScrubbed(unittest.TestCase):

    def test_nothing_that_names_a_machine_a_path_or_a_secret_leaves(self):
        out = TB.scrub(DIRTY)
        for bad in ("/Users/", "/private/tmp", "192.0.2.7", "player@", "someone@example.com", ".local",
                    "C:\\Users", "gh" + "p_", "@"):
            self.assertNotIn(bad, out, "%r left the Mac in %r" % (bad, out))
        self.assertIn("<path>", out)
        self.assertIn("v3864", TB.scrub("v3864 and #233 and REG-3180 stay"), "the scrub ate a version number")

    def test_the_board_holds_its_cards_by_status_and_counts_them(self):
        b = TB.board([_card(2, "pending", "two", DIRTY), _card(1, "in_progress", "one"), _card(3, "completed", "three"),
                      _card(10, "bogus", "ten")], "D2R - the board", T0)
        self.assertEqual([c["id"] for c in b["cards"]], ["1", "2", "3", "10"], "cards out of id order")
        self.assertEqual(b["counts"], {"in_progress": 1, "pending": 2, "completed": 1}, "an unknown status is not pending")
        self.assertNotIn("/Users/", json.dumps(b), "a description left unscrubbed")
        self.assertEqual(b["at"], T0)

    def test_a_huge_board_gives_up_words_never_cards(self):
        cards = [_card(i, "pending", "card %d" % i, "x" * 5000) for i in range(150)]
        b = TB.board(cards, "big", T0)
        self.assertEqual(len(b["cards"]), 150, "a card was dropped to fit")
        self.assertLessEqual(len(json.dumps(b, ensure_ascii=False).encode("utf-8")), TB.BOARD_MAX_BYTES)


class ItIsPostedAtItsOwnPace(unittest.TestCase):

    def test_first_change_and_refresh(self):
        b = TB.board([_card(1, "pending", "one")], "t", T0)
        self.assertEqual(TB.due({}, b, T0)[0], True)
        st = {"hash": TB.digest(b), "at": T0}
        b2 = TB.board([_card(1, "completed", "one")], "t", T0 + 1000)
        self.assertEqual(TB.due(st, b2, T0 + 60 * 1000)[0], False, "a change posted inside the 2 min gap")
        self.assertEqual(TB.due(st, b2, T0 + TB.POST_MIN_GAP_MS)[0], True)
        same = TB.board([_card(1, "pending", "one")], "t", T0 + 5000)
        self.assertEqual(TB.digest(same), st["hash"], "the time is part of the fingerprint")
        self.assertEqual(TB.due(st, same, T0 + 10 * 60 * 1000)[0], False, "an unchanged board re-posted at once")
        self.assertEqual(TB.due(st, same, T0 + TB.POST_REFRESH_MS)[0], True)


class OnlyHisMacPublishesIt(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="taskboard-law-")
        os.makedirs(os.path.join(self.d, "session-x"))
        for c in (_card(1, "in_progress", "ship v3864", DIRTY), _card(2, "pending", "the next one")):
            with io.open(os.path.join(self.d, "session-x", "%s.json" % c["id"]), "w", encoding="utf-8") as fh:
                json.dump(c, fh)
        self.posts = []
        self._saved = dict(CA._TASK_BOARD)
        CA._TASK_BOARD.update(state={}, posted=0)

    def tearDown(self):
        CA._TASK_BOARD.clear(); CA._TASK_BOARD.update(self._saved)
        shutil.rmtree(self.d, ignore_errors=True)

    def _post(self, url, body, keypath):
        self.posts.append((url, body))
        return {"ok": True}

    def _run(self, **kw):
        with mock.patch.object(CA, "_beacon_suppressed_by", return_value=kw.pop("held", None)), \
                mock.patch.object(CA, "_task_board_state_path", return_value=os.path.join(self.d, "state.json")):
            return CA.task_board_publish_once(now_ms=kw.pop("now", T0), _post=self._post, _tasks_dir=self.d,
                                              _label=kw.pop("label", "Konyo · Mac"), _platform=kw.pop("plat", "darwin"))

    def test_his_mac_posts_a_scrubbed_signed_board_once(self):
        r = self._run()
        self.assertTrue(r["posted"], r)
        url, body = self.posts[0]
        self.assertEqual((url, body["kind"], body["poster"]), (CA._ROSTER_URL, "tasks", "Konyo · Mac"))
        self.assertEqual(len(body["board"]["cards"]), 2)
        self.assertNotIn("/Users/", json.dumps(body), "the posted board carries a home path")
        self.assertFalse(self._run(now=T0 + 1000)["posted"], "an unchanged board was posted again at once")

    def test_a_board_dir_that_will_not_list_is_unknown_never_empty(self):
        # Routine M (RANK 1): a failed listing read as "no sessions" - an empty board nobody measured
        # REG-3629 (#107 leftover): chmod(0) cannot unlist a directory on Windows, so the same
        # door is driven there through a listdir PermissionError. POSIX still uses a real mode-0 dir.
        self.assertEqual(TB.session_dirs(os.path.join(self.d, "never-made")), [], "a missing board dir is not 'no board'")
        locked = os.path.join(self.d, "locked")
        os.makedirs(locked)

        def _assert_unlistable():
            self.assertIsNone(TB.session_dirs(locked), "a board dir that would not list read as an empty board")
            r = self._run_dir(locked)
            self.assertFalse(r["posted"], r)
            self.assertIn("UNKNOWN", r["why"])

        if os.name == "nt":
            real_listdir = os.listdir
            locked_key = os.path.normcase(os.path.realpath(locked))

            def listdir(path, *a, **k):
                try:
                    if os.path.normcase(os.path.realpath(path)) == locked_key:
                        raise PermissionError("REG-3629: chmod cannot unlist a Windows directory")
                except PermissionError:
                    raise
                except OSError:
                    pass
                return real_listdir(path, *a, **k)

            with mock.patch("os.listdir", listdir):
                _assert_unlistable()
            return
        os.chmod(locked, 0)
        try:
            if os.access(locked, os.R_OK):
                self.skipTest("this account reads a mode-0 dir (root) - the refusal cannot be staged here")
            _assert_unlistable()
        finally:
            os.chmod(locked, 0o755)

    def _run_dir(self, d):
        with mock.patch.object(CA, "_beacon_suppressed_by", return_value=None), \
                mock.patch.object(CA, "_task_board_state_path", return_value=os.path.join(self.d, "state.json")):
            return CA.task_board_publish_once(now_ms=T0, _post=self._post, _tasks_dir=d, _label="Konyo · Mac",
                                              _platform="darwin")

    def test_no_other_pc_and_no_suppressed_console_posts(self):
        self.assertFalse(self._run(plat="win32")["posted"])
        self.assertFalse(self._run(label="Dean")["posted"])
        self.assertFalse(self._run(held="ci")["posted"])
        self.assertEqual(self.posts, [], "a board was posted from a PC that does not publish it")


class TheSiteKeepsItAndTheConsoleOpensIt(unittest.TestCase):

    def test_the_worker_takes_it_only_from_an_approver_and_paces_its_writes(self):
        js = io.open(os.path.join(ROOT, "functions", "api", "roster.js"), encoding="utf-8").read()
        for needle in ('if (body.kind === "tasks") return tasksPost(env, bytes, sig, body);',
                       "if (wantTasks !== null) return tasksGet(kv);"):
            self.assertIn(needle, js, "the route never reaches the board")
        # the worker itself, in node, on a fake KV: a stranger, an unsigned post, a good one, and a second inside the minute
        pub = "A" * 43                                   # 32 zero bytes, base64url - a fixture key, never a real one
        prog = """
import('%s').then(async m => {
  const kv = { s: { 'rosterkey:Konyo · Mac': JSON.stringify({ pub: '%s', keyId: 'fixture' }),
                    'rosterkey:Dean': JSON.stringify({ pub: '%s', keyId: 'fixture' }) },
               async get(k) { return this.s[k] === undefined ? null : this.s[k]; }, async put(k, v) { this.s[k] = v; } };
  const env = { TZ_HISTORY: kv };
  const bytes = new Uint8Array(64);
  const good = { state: 'valid', pub: '%s', keyId: 'fixture' };
  const board = { title: 't', at: 1, counts: {}, cards: [{ id: '1' }] };
  const post = async (poster, sig) => (await m.tasksPost(env, bytes, sig, { kind: 'tasks', poster, board, signedAt: Date.now() })).json();
  const out = {};
  out.none = await (await m.tasksGet(kv)).json();
  out.stranger = await post('Dean', good);
  out.unsigned = await post('Konyo · Mac', { state: 'none' });
  out.good = await post('Konyo · Mac', good);
  out.again = await post('Konyo · Mac', good);
  out.read = await (await m.tasksGet(kv)).json();
  console.log(JSON.stringify(out));
});""" % (__import__("pathlib").Path(ROOT, "functions", "api", "roster.js").as_uri(), pub, pub, pub)   # v3886 (#107) - a file URL
        r = subprocess.run(["node", "--input-type=module", "-"], input=prog, capture_output=True, text=True,
                           encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertIsNone(out["none"]["board"], "an unpublished board read as a board")
        self.assertIs(out["stranger"]["ok"], False, "a PC that is not an approver published the board: %r" % out["stranger"])
        self.assertIs(out["unsigned"]["ok"], False, "an unsigned board was kept: %r" % out["unsigned"])
        self.assertIs(out["good"]["ok"], True, "his Mac's signed board was refused: %r" % out["good"])
        self.assertIs(out["again"]["ok"], False, "a second board inside the minute was kept: %r" % out["again"])
        self.assertEqual((out["read"]["by"], out["read"]["board"]["cards"]), ("Konyo · Mac", [{"id": "1"}]))

    def test_the_route_opens_only_its_one_page_behind_the_origin_gate(self):
        seen = []
        self.assertTrue(CA.task_board_open(_open=seen.append)["ok"])
        self.assertEqual(seen, ["https://bull-4-u.com/d2r/tasks.html"])
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = src.index('        if path == "/api/open_tasks":')
        block = src[i:src.index("        if path == ", i + 10)]
        g = block.find("            if not _d2jsp.console_may_post(")
        self.assertGreater(g, 0, "the route no longer asks the origin gate - another tab may open windows here")
        self.assertIn("                self._json(403, ", block[g:], "the gate's refusal no longer refuses")
        o = block.find("            self._json(200, task_board_open())")
        self.assertGreater(o, g, "the route opens something other than its one page, or before the gate")

    def test_the_footer_button_sits_beside_history_and_asks_the_route(self):
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        self.assertIn('>Future</button>', ui[ui.index('<button id="foot-tasks"'):ui.index('</button>', ui.index('<button id="foot-tasks"')) + 9],
                      "the footer button is not named Future (his name for it, 2026-11-05)")
        self.assertIn('title="Version history">history</button><span class="dot">·</span><button id="foot-tasks"', ui,
                      "the tasks button is not beside history at the bottom left")
        self.assertIn("fetch('/api/open_tasks', { method: 'POST'", ui)

    def test_the_page_draws_text_never_markup_and_ships(self):
        page = io.open(os.path.join(HERE, "tasks_board.html"), encoding="utf-8").read()
        script = page[page.index("<script>"):]
        self.assertNotIn("innerHTML", script, "the page draws a card's words as markup")
        self.assertIn("fetch('/api/roster?tasks=1'", script)
        self.assertIn("UNKNOWN, not empty", script, "a failed read draws an empty board")
        dep = io.open(os.path.join(ROOT, "deploy.sh"), encoding="utf-8").read()
        self.assertIn('cp tv/tasks_board.html "$DIST/d2r/tasks.html"', dep, "the page is never deployed")


RED_PROOF = [
    {"why": "v3864 (Routine M) - a board dir that will not list reads as an empty board",
     "file": "tv/task_board.py",
     "find": "    except FileNotFoundError:\n        return []\n    except OSError:\n        return None\n",
     "replace": "    except FileNotFoundError:\n        return []\n    except OSError:\n        return []\n",
     "matches": 1},
    {"why": "v3864 - a home path leaves the Mac on the public board",
     "file": "tv/task_board.py",
     "find": "    (re.compile(r\"/(?:Users|home)/[^/\\s'\\\"`)]+(?:/[^\\s'\\\"`)]*)?\"), \"<path>\"),\n",
     "replace": "",
     "matches": 1},
    {"why": "v3864 - a PC that is not an approver publishes the board",
     "file": "tv/control_app.py",
     "find": "    if label not in ROSTER_APPROVERS:\n        return {\"posted\": False, \"why\": \"this PC does not publish the board\"}\n",
     "replace": "",
     "matches": 1},
    {"why": "v3864 - a change is posted inside the 2 min gap",
     "file": "tv/task_board.py",
     "find": "        return (gap >= POST_MIN_GAP_MS), (",
     "replace": "        return True, (",
     "matches": 1},
    {"why": "v3864 - the route opens something other than its one page",
     "file": "tv/control_app.py",
     "find": "            self._json(200, task_board_open())\n",
     "replace": "            self._json(200, {\"ok\": True})\n",
     "matches": 1},
    {"why": "v3864 - the route no longer asks the origin gate, so another tab opens windows on his PC",
     "file": "tv/control_app.py",
     "find": "            if not _d2jsp.console_may_post(\n                    self.headers.get(\"Origin\"), self.headers.get(\"Host\"), CONTROL_PORT,\n                    self.headers.get(\"Sec-Fetch-Site\")):\n                self._json(403, {\"ok\": False, \"reason\": \"local\"})\n                return\n            self._json(200, task_board_open())\n",
     "replace": "            self._json(200, task_board_open())\n",
     "matches": 1},
    {"why": "v3864 - the worker keeps a board from a PC that is not an approver",
     "file": "functions/api/roster.js",
     "find": "  if (APPROVERS.indexOf(poster) === -1) return refuse(\"roster would not take this board: \"",
     "replace": "  if (false) return refuse(\"roster would not take this board: \"",
     "matches": 1},
    {"why": "v3864 - the worker keeps an unsigned board",
     "file": "functions/api/roster.js",
     "find": "  if (intent.refused || intent.verified !== true || intent.register) {\n    return refuse(\"roster would not take this board: \"",
     "replace": "  if (false) {\n    return refuse(\"roster would not take this board: \"",
     "matches": 1},
    {"why": "v3864 - the worker keeps a second board inside the minute",
     "file": "functions/api/roster.js",
     "find": "  if (prev && typeof prev.at === \"number\" && now - prev.at < TASKS_MIN_GAP_MS) {\n",
     "replace": "  if (false) {\n",
     "matches": 1},
    {"why": "v3864 - the page is not shipped",
     "file": "deploy.sh",
     "find": "cp tv/tasks_board.html \"$DIST/d2r/tasks.html\"",
     "replace": "true",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
