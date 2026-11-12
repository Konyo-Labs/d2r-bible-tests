# -*- coding: utf-8 -*-
"""v3902 (REG-3777) - THE SHIP'S POST-LAND CHECK READS THE VERSION HIS CONSOLE ACTUALLY SENDS.

MEASURED 11-12 08:35 on v3900's landing: "ship: post-land /api/status says None, expected v3900 - the live console has not
moved onto this version yet". His console's /api/status said {"ver": "v3899", "liveVer": "v3899", "bibleVer": "v3899"} at
that moment: post_land_status asked for "version", "build" and "ship.version" - names the console never sends - so it said
None after every ship and had never once measured whether the live console moved. It reads "ver" (the stamp bump_version
writes into control_app.py) first now: "says 'v3899', expected v3900" before the console pulls, "is v3900" after.

DRIVEN: the real ship_when_green.post_land_status against a throwaway HTTP server on 127.0.0.1:<ephemeral> serving the
console's own key shape (never :17772). RED_PROOF below.
"""
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ship_when_green as SW  # noqa: E402


def _serve(body):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            raw = json.dumps(body).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, "http://127.0.0.1:%d/api/status" % srv.server_address[1]


class ThePostLandCheckReadsTheConsolesVer(unittest.TestCase):

    def _said(self, body, version="v3900"):
        srv, url = _serve(body)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        said = []
        SW.post_land_status(version, None, said.append, url=url)
        return " | ".join(said)

    def test_the_console_before_it_pulls_is_named(self):
        """* THE POINT - 11-12 08:35: his console said ver v3899 and the line said None"""
        line = self._said({"ok": True, "ver": "v3899", "liveVer": "v3899", "bibleVer": "v3899"})
        self.assertIn("'v3899'", line, "the console's own version was not read: %s" % line)
        self.assertIn("expected v3900", line)

    def test_the_console_on_the_version_is_said_so(self):
        line = self._said({"ok": True, "ver": "v3900"})
        self.assertIn("post-land /api/status is v3900", line, line)

    def test_baseline_a_body_with_no_version_key_says_none(self):
        line = self._said({"ok": True})
        self.assertIn("says None", line, "PREMISE: a body with no version at all no longer says None - the case would "
                                         "not distinguish")


RED_PROOF = [
    {"why": "REG-3777 - the post-land check stops reading the console's ver and says None after every ship again",
     "file": "tv/ship_when_green.py",
     "find": "        have = (data.get(\"ver\") or data.get(\"version\") or data.get(\"build\")\n",
     "replace": "        have = (data.get(\"version\") or data.get(\"build\")\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
