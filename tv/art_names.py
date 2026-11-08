"""Every picture the console and its board can ask /art/ for, read from the code that asks. -> names

REG-3206 (2026-11-05, GrokBot v3864): the guest console logged ~103 distinct /art/* 404s and 581
failed requests. Nothing in the repo could answer "which art names can this console request, and
are they all in this art tree?", so a missing picture was only ever found by someone looking at the
glass. That guest's art/ held 21 files (GrokBot's own scratch stage, not this repo's mirror): run
`python3 tv/art_names.py --art <its art dir>` there: it counts every name that dir lacks and lists the first 40.

WHERE THE NAMES COME FROM. Two pages ask /art/ for pictures: tv/control_ui.html (absolute
`/art/<file>`) and the board, bible.html, which the console iframes from /board, so its relative
`art/<file>` resolves to /art/ too. Most names are written out whole; the rest are COMPOSED in
code (`'art/' + b.art`, `'art/tz_' + slug + '.jpg'`, ...). Each composer is a DOOR, and each door
is read here from the table that feeds it. A composer this module does not know is reported as an
unknown door rather than skipped, so a new one cannot quietly fall outside the check.

The HD manifest (art/HD_ART_MANIFEST.json) is folded into the board's art table at runtime, so its
items are names the console can ask for as well.

Read-only: it opens the two pages and the manifest, and lists art/.
"""
import bisect
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

_EXT = r"(?:png|gif|jpe?g|webp|svg)"
# v3868 (the Grok CLI on REG-3206, #231 6675924693) - a name may carry inner dots (hd.unique.png) and an upper-case
# extension (Korlic.GIF): the old pattern recorded neither, and neither became an unknown door. None exists today
# (measured: the wider pattern adds 0 names), so this closes a gap without moving a count.
_FILE = r"[A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+)*\.(?i:png|gif|jpe?g|webp|svg)"
# `art/<file>` or `/art/<file>`, never `frames/art/...` or `hd_art/...`
_LITERAL = re.compile(r"(?<![A-Za-z0-9_\-./])/?art/(" + _FILE + r")(?![A-Za-z0-9_\-])")
# a composer: a string that ENDS in art/ (or art/<prefix>) and is followed by `+`, or TZ_ART_BASE +
_COMPOSER = re.compile(r"(?<![A-Za-z0-9_\-./])/?art/[A-Za-z0-9_\-]*['\"`]\s*\+|\bTZ_ART_BASE\s*\+")

# Every composer this module knows, by the text that follows it -> the feed that expands it.
# (page, signature regex matched at the composer, feed)
DOORS = (
    ("bible.html", r"art/'\+file\+'\" alt=\"'\+alt", "art-props"),            # _essArt, _wsArt
    ("bible.html", r"TZ_ART_BASE\+slug\+'_graphic\.png'", "tz-zone-art"),     # _tzArtSrc
    ("bible.html", r"art/'\+SLOT\[s\]\+'_graphic\.png'", "craft-slots"),      # _wireCraftArt
    ("bible.html", r"art/' \+ file \+ '\" alt=\"\" loading", "branch-emblems"),
    ("bible.html", r"art/'\+BM\[k\]", "base-map"),                            # rare/magic base art
    ("bible.html", r"art/gem_' \+ g\.name", "gems"),
    ("bible.html", r"art/' \+ b\.art", "art-props"),                          # UBER_BOSSES
    ("bible.html", r"art/tz_'\+art\+'\.jpg", "tz-info"),
    ("bible.html", r"art/'\+f\+'\" alt=\"\" loading", "tab-icons"),
    ("bible.html", r"art/' \+ pic\)", "boss-portraits"),
    ("bible.html", r"TZ_ART_BASE \+ 'tz_' \+ slug", "tz-info"),
    ("tv/control_ui.html", r"/art/tz_' \+ file \+ '\.jpg", "console-tz-info"),
    # REG-3298 (v3875's GitHub round, the agent suite) - v3874's Quick wins tiles composed three art paths the law had
    # never met, so the picture law answered UNKNOWN on GitHub while every name they ask for was in art/
    ("bible.html", r"art/tz_' \+ slug \+ '\.jpg'", "tz-info"),                 # _qwZoneArt
    ("bible.html", r"art/' \+ bp :", "boss-portraits"),                       # _qwTile, a boss with a portrait
    ("bible.html", r"art/' \+ su :", "qw-su-sprites"),                        # _qwTile, a superunique's sprite
    ("bible.html", r"art/' \+ _QW_SU_ART\[r\.bossId\]", "qw-su-sprites"),      # v3887 (#155) - _runArtThumb, a super-unique Best run
    # #108 - a random-pack monster's family sprite (The Arreat Summit), by name: the tile and the D2IO_ART fill
    ("bible.html", r"art/' \+ pk :", "monster-packs"),                        # _qwTile, a random pack's sprite
    ("bible.html", r"art/' \+ MONSTER_PACK_ART\[k\]", "monster-packs"),       # D2IO_ART, the floating card
    ("bible.html", r"art/' \+ ar :", "area-runs"),                            # _qwTile, an area run's own place (The Pit)
    ("tv/control_ui.html", r"/art/' \+ mon \+ '\"", "console-tz-monsters"),    # #108 - a Terror Zone's own monster
    ("bible.html", r"art/'\+mon\+'\"", "board-tz-monsters"),                    # #108 - the board's Terror Zone rows, the same table
)


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def in_comment(src, pos):
    """Is the text at `pos` inside a comment? A local judgment, region-aware. -> bool

    Inside a <script> or <style> block: a `//` earlier on the line, or an unclosed `/*` since the
    block began. In markup: an unclosed `<!--`. Markup is never searched for `/*` because the page
    carries `accept="image/*"` attributes, which read as an opening comment to a naive scan."""
    marks = _marks(src)

    def last(tok, lo=0):
        ps = marks[tok]
        k = bisect.bisect_left(ps, pos) - 1
        return ps[k] if k >= 0 and ps[k] >= lo else -1

    lo, lc, so, sc = last("<script"), last("</script>"), last("<style"), last("</style>")
    start = None
    if lo > lc:
        start = src.find(">", lo) + 1
    elif so > sc:
        start = src.find(">", so) + 1
    if start is None or start > pos:
        return last("<!--") > last("-->")
    nl = src.rfind("\n", start, pos)
    if re.search(r"(?:^|[\s;{}(),])//", src[(nl + 1) if nl >= 0 else start:pos]):
        return True
    return last("/*", start) > last("*/", start)


_MARKS = {}


def _marks(src):
    """Sorted positions of each comment/region token in src, found once per page. -> dict"""
    key = (len(src), hash(src))
    got = _MARKS.get(key)
    if got is None:
        got = {}
        for tok in ("<script", "</script>", "<style", "</style>", "<!--", "-->", "/*", "*/"):
            got[tok] = [m.start() for m in re.finditer(re.escape(tok), src)]
        _MARKS.clear()
        _MARKS[key] = got
    return got


def _object_values(src, anchor, quote="'"):
    """String values of the object literal that starts at `anchor` (the one occurrence). -> list"""
    i = src.find(anchor)
    if i < 0:
        return []
    j = src.find("};", i)
    body = src[i + len(anchor):j if j > 0 else len(src)]
    return re.findall(r":\s*" + quote + r"([^" + quote + r"]+)" + quote, body)


def _tz_keys(src):
    """The art key (third column) of every zone in the page's TZ_INFO table. -> set"""
    m = re.search(r"\bvar TZ_INFO = (\{.*?\});|\bconst TZ_INFO = (\{.*?\});", src)
    if not m:
        return set()
    try:
        table = json.loads(m.group(1) or m.group(2))
    except ValueError:
        return set()
    return set(v[2] for v in table.values() if isinstance(v, list) and len(v) > 2 and v[2])


def _gem_files(src):
    m = re.search(r"const GEM_TYPES = (\[.*?\]);\n", src)
    if not m:
        return []
    # v3865 (GitHub's swallow ratchet) - a GEM_TYPES the page carries but that will not parse is a FAILED read: it raises,
    # so the law goes red, never a shorter list of names that passes while a gem picture is missing
    types = json.loads(m.group(1))
    out = []
    for t in types:
        for q in t.get("q") or []:
            slug = re.sub(r"[^a-z0-9]+", "_", str(q.get("name") or "").lower()).strip("_")
            if slug:
                out.append("gem_" + slug + ".png")
    return out


def _feeds(board, console, manifest):
    """feed name -> list of art file names (no `art/` prefix)."""
    f = {}
    f["console-literal"] = _LITERAL.findall(console)
    f["board-literal"] = _LITERAL.findall(board)
    f["manifest"] = [v[len("art/"):] for v in (manifest.get("items") or {}).values()
                     if isinstance(v, str) and v.startswith("art/")]
    f["art-props"] = re.findall(r"\bart:\s*'(" + _FILE + r")'", board)
    f["tz-zone-art"] = [v + "_graphic.png" for v in _object_values(board, "const TZ_ZONE_ART = {", '"')
                        if not v.startswith(("data:", "http", "/", "banners/"))]
    f["craft-slots"] = [v + "_graphic.png" for v in _object_values(board, "var SLOT = {")]
    f["branch-emblems"] = re.findall(r"branchEmblem\('(" + _FILE + r")'", board)
    bm = re.search(r"var BM=\{(.*?)\};", board)
    f["base-map"] = re.findall(r":'(" + _FILE + r")'", bm.group(1)) if bm else []
    f["gems"] = _gem_files(board)
    f["tz-info"] = ["tz_%s.jpg" % k for k in sorted(_tz_keys(board))]
    f["tab-icons"] = [v for v in _object_values(board, "TAB_ICON = {") if re.match(_FILE + "$", v)]
    f["boss-portraits"] = [v for v in _object_values(board, "BOSS_PORTRAIT = {") if re.match(_FILE + "$", v)]
    f["console-tz-info"] = ["tz_%s.jpg" % k for k in sorted(_tz_keys(console))]
    f["qw-su-sprites"] = [v for v in _object_values(board, "var _QW_SU_ART = {") if re.match(_FILE + "$", v)]
    f["monster-packs"] = [v for v in _object_values(board, "const MONSTER_PACK_ART = {", quote='"') if re.match(_FILE + "$", v)]
    f["area-runs"] = [v for v in _object_values(board, "const AREA_RUN_ART = {", quote='"') if re.match(_FILE + "$", v)]
    f["console-tz-monsters"] = [v for v in _object_values(console, "var TZ_MONSTER = {", quote='"') if re.match(_FILE + "$", v)]
    f["board-tz-monsters"] = [v for v in _object_values(board, "  var TZ_MONSTER = {", quote='"') if re.match(_FILE + "$", v)]
    return f


def doors(board, console):
    """Every composer in the two pages, each with the feed that expands it or None. -> list of dicts"""
    out = []
    for page, src in (("bible.html", board), ("tv/control_ui.html", console)):
        for m in _COMPOSER.finditer(src):
            at = src[m.start():m.start() + 80]
            feed = None
            for p, sig, fd in DOORS:
                if p == page and re.match(sig, at):
                    feed = fd
                    break
            out.append({"page": page, "line": src.count("\n", 0, m.start()) + 1,
                        "text": at.split("\n", 1)[0][:60], "feed": feed})
    return out


def names(repo=None, board_path=None, console_path=None):
    """Every art file name the console can request. -> dict
    {names: {file: [feed, ...]}, feeds: {feed: n}, doors: [...], unknownDoors: [...]}"""
    repo = repo or REPO
    board = _read(board_path or os.path.join(repo, "bible.html"))
    console = _read(console_path or os.path.join(repo, "tv", "control_ui.html"))
    # v3865 (GitHub's swallow ratchet) - the HD manifest is a tracked file; one that will not read raises, never an empty
    # manifest whose names silently drop out of the census
    manifest = json.loads(_read(os.path.join(repo, "art", "HD_ART_MANIFEST.json")))
    feeds = _feeds(board, console, manifest)
    by_name = {}
    for feed, files in feeds.items():
        for n in files:
            by_name.setdefault(n, [])
            if feed not in by_name[n]:
                by_name[n].append(feed)
    # A name written only inside comments is not asked for by any code. Kept in `names` (a comment
    # naming a file that is gone is still worth reading) and listed apart, so a caller decides.
    code = set()
    for src in (board, console):
        for m in _LITERAL.finditer(src):
            if not in_comment(src, m.start()):
                code.add(m.group(1))
    comment_only = sorted(n for n, fs in by_name.items()
                          if set(fs) <= {"board-literal", "console-literal"} and n not in code)
    ds = doors(board, console)
    return {"names": by_name,
            "commentOnly": comment_only,
            "feeds": dict((k, len(v)) for k, v in feeds.items()),
            "doors": ds,
            "unknownDoors": [d for d in ds if d["feed"] is None]}


def missing(found, art_dir):
    """Names the console can request that are not files under art_dir. -> sorted list

    Compared against ONE listing, by exact case: a Mac's disk answers isfile('korlic.gif') for
    Korlic.gif, and the Linux guest and a case-sensitive server 404 it. An art dir that will not
    list is not 'nothing missing' - every name is reported."""
    try:
        have = set(f for f in os.listdir(art_dir) if os.path.isfile(os.path.join(art_dir, f)))
    except OSError:
        have = set()
    return sorted(n for n in found["names"] if n not in have)


def main(argv=None):
    """CLI for the guest refresh: check the names a board (and this console) ask for against an art
    tree. Exit 0 = every name is there, 1 = some are not (listed), 2 = a page would not read."""
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--board", help="the board HTML to read (default: bible.html)")
    ap.add_argument("--art", help="the art tree to check (default: art/)")
    a = ap.parse_args(argv)
    try:
        found = names(board_path=a.board)
    except (OSError, UnicodeDecodeError) as e:
        print("  art check: a page would not read (%s) - UNKNOWN" % str(e)[:80])
        return 2
    gone = [n for n in missing(found, a.art or os.path.join(REPO, "art"))
            if n not in found["commentOnly"]]
    print("  art check: %d name(s) the console can ask /art/ for, %d door(s), %d unknown door(s)"
          % (len(found["names"]) - len(found["commentOnly"]), len(found["doors"]),
             len(found["unknownDoors"])))
    for d in found["unknownDoors"]:
        print("  ? unknown art door %s:%d %s" % (d["page"], d["line"], d["text"]))
    # v3868 (the Grok CLI on REG-3206) - A KNOWN DOOR WHOSE FEED READ NOTHING EXPANDS TO NOTHING: its anchor moved (a
    # declaration re-spaced, a table re-quoted) and every picture behind it went unchecked while this said "ok".
    blind = sorted(set(d["feed"] for d in found["doors"] if d["feed"] and not found["feeds"].get(d["feed"])))
    for fd in blind:
        print("  ? the %r feed read no names - the door it expands is unchecked (its anchor moved)" % fd)
    for n in gone[:40]:
        print("  x MISSING art/%s (asked by %s)" % (n, ", ".join(found["names"][n])))
    if gone:
        print("  %d name(s) will 404 on a console that serves this art tree" % len(gone))
        return 1
    if found["unknownDoors"] or blind:
        # v3868 - an unchecked door is not "every one is in the tree": UNKNOWN, the same exit as a page that won't read
        print("  UNKNOWN - %d unknown door(s) and %d empty feed(s): what they ask for was never checked"
              % (len(found["unknownDoors"]), len(blind)))
        return 2
    print("  ok - every one is in the art tree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
