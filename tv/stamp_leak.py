# -*- coding: utf-8 -*-
"""v3774 (REG-2295) — WHAT A VERSION STAMP MAY CARRY, AND WHAT IT MAY NOT.

The build name and note land in bible.html (twice), WINDOWS_SHIP.json and TASKS.md of a PUBLIC repo.
bump_version.py refuses a leaking name or note before writing, and gate_ledger.py runs the same check
on every ADDED stamp line before it lets a coherent bump carry the content gates, so a note pasted by
hand past the tool still reruns them. Both callers also ask free_text_problem, which admits only
inert words. One definition, two callers.
"""
import re

# THE NAME AND NOTE ARE PUBLISHED FREE TEXT. They land in bible.html (twice),
# WINDOWS_SHIP.json and TASKS.md of a PUBLIC repo, and gate memory skips content gates over a coherent
# bump. leak_problem refuses home paths (every spelling), IPv4/IPv6, private hostnames, tokens and this
# machine's identity; free_text_problem refuses anything but inert words.
# The home-path ratchet's own pattern (test_no_new_home_path_is_published.HOME), pinned equal by the guard
# test. A production module may not import a test module, so it is copied. The gate's pattern stays as it
# is: it is a RATCHET over 113+ existing literals, and widening it raises the count in 20 tracked files
# (measured), which only a human baseline rewrite may accept. The leak check below is WIDER: it is
# applied to new free text only, so it can be strict without touching history.
HOME = re.compile(r"/Users/[A-Za-z0-9._-]+/")
_SEP = r"(?:/|%2f|&#0*47;|&#x0*2f;|\\{1,2})"
_HOME_ANY = re.compile(HOME.pattern + "|" + _SEP + r"(?:users|home)" + _SEP + r"[a-z0-9._-]+|/root(?:/|\b)|\b[a-z]:" + _SEP + r"users\b", re.I)
_LEAK_IP = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_LEAK_IP6 = re.compile(r"(?<![\w:])(?:[0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4}(?![\w:])", re.I)
_LEAK_HOST = re.compile(r"\b[A-Za-z0-9-]+\.(?:local|lan|internal|localdomain|home\.arpa|ts\.net)\b", re.I)
_LEAK_TOKEN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|"
                         r"glpat-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{30,}|"
                         r"xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"
                         r"|\bbearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I)

# THE NAME AND NOTE ARE INERT OR THEY ARE NOT ACCEPTED. Content gates rule on these files' text (counts
# of a URL, forbidden strings, syntax). A note limited to words, digits, spaces and - , ( ) + # cannot
# form a URL, a path, markup, a quote or an escape, so it cannot change what such a gate counts unless
# the gate looks for a plain word, and gate_ledger reruns any gate whose own script holds one of the
# note's words. A period is allowed only at the end of a sentence (followed by a space or the end).
# The apostrophe and ampersand are left out: one breaks the JS literal, the other becomes &amp;.
FREE_TEXT_MAX = 120
_FREE_BAD = re.compile(r"[^A-Za-z0-9 ,()+#.\-]")
_FREE_DOT = re.compile(r"\.(?! |$)")


def free_text_problem(text):
    """Why this name or note is not inert free text, or None. -> str|None"""
    t = str(text if text is not None else "")
    if len(t) > FREE_TEXT_MAX:  # FREE-MAX
        return "longer than %d characters" % FREE_TEXT_MAX
    m = _FREE_BAD.search(t)
    if m:  # FREE-CHARS
        return "the character %r (only letters, digits, spaces and - , ( ) + # . are allowed)" % m.group(0)
    if _FREE_DOT.search(t):  # FREE-DOT
        return "a period inside a word (a file name, a domain or a number)"
    return None


def leak_problem(text, machine=True):
    """Why this free text may not be published, or None. -> str|None

    `machine` False leaves out the one check that reads THIS machine (its home path and user name): REG-3191 - a
    proof's KEY must be the same on every machine. heart2._inert asks with machine=False; a bump and the gate ledger,
    which guard what is published from here, keep asking it."""
    t = str(text or "")
    if _HOME_ANY.search(t):  # BUMP-LEAK-HOME-ANY
        return "a home path (any spelling: escaped, encoded, Windows, /home, /root)"
    if _LEAK_IP.search(t):  # BUMP-LEAK-IP
        return "an IP address"
    if any(":" in m.group(0) and (re.search(r"[a-f]", m.group(0), re.I) or "::" in m.group(0))
           for m in _LEAK_IP6.finditer(t)):  # BUMP-LEAK-IP6
        return "an IPv6 address"
    if _LEAK_HOST.search(t):  # BUMP-LEAK-HOST
        return "a hostname"
    if _LEAK_TOKEN.search(t):  # BUMP-LEAK-TOKEN
        return "a token"
    if not machine:
        return None
    try:
        import guest_profile as _gp
        for secret, _repl in _gp._secrets():
            if secret == "Konyo" or len(secret) < 4:
                continue  # the public nickname is not a secret
            if secret in t:  # BUMP-LEAK-MACHINE
                return "this machine's identity (home or user name)"
    except Exception:
        pass
    return None
