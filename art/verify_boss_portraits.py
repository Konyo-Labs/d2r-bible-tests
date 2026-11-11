#!/usr/bin/env python3
"""v1643 — guard the TWELVE boss portraits against being silently swapped again, and guard the ONE
remaining deliberate refusal (pit — an area farm, not a boss) against being silently "fixed".

v1643 also made this file a GATE instead of a document: it now runs from hooks/pre-push, so a
push that breaks the manifest/app agreement is blocked. It sat in the repo with ZERO automated
callers — never in pre-push, never in any of the eight CI workflows, never in package.json or
tests/ — passing its own hand-run and guarding nothing (REG-130).

WHAT THIS DOES AND, MORE IMPORTANTLY, WHAT IT DOES NOT DO.

It compares the bytes on disk against art/boss_portraits.manifest.json, which records the sha256 of
each portrait AS A HUMAN LAST OPENED IT, next to a sentence saying what that human saw. That is the
whole trick. The hash proves nothing about content; it proves only "these are still the bytes
somebody looked at". A CHANGED verdict is therefore not a failure — it is a request for a person to
open the image and either bless the new pixels or restore the old ones.

Why the bar is that low: art/mephisto_graphic.png shipped as a blue soulstone gem and
art/diablo_graphic.png as a leather-bound book from v269 (2026-06-14) to v1636 (2026-08-04), and
EVERY automated check passed for seven weeks. The path resolved. naturalWidth was > 0. An md5 sweep
of art/ found zero duplicates. File size flagged Mephisto at 10KB and sailed straight past Diablo at
46KB, which was a book. v1629 then "fixed" the bug by confirming the filename in the map. A file
that loads is not a file that is right, and no checker that never opens an image can tell you which
you have — so this one does not pretend to.

The cause was a fuzzy base-item matcher in v269 that rewrote 230 art/*_graphic.png files from item
art and had no idea that two of its slugs, 'mephisto' and 'diablo', name BOSSES as well as items
(Mephisto's Soulstone; a tome). Those two filenames are permanently ambiguous. Anything that bulk-
writes art/ by name must skip them, and this script is how the next bulk write gets caught.

    python3 art/verify_boss_portraits.py          # exit 0 all match, 1 something changed/missing
    python3 art/verify_boss_portraits.py --list   # print the human descriptions, check nothing

To re-bless a portrait: OPEN IT, decide in words what it depicts, then update 'depicts', 'bytes' and
'sha256' for that row in the manifest. Editing the hash without opening the image reintroduces
exactly the bug this file exists to prevent.
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "boss_portraits.manifest.json")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")

# v1643 — ids that must carry a human-verified portrait, not a level-art fallback and not a
# _declined note. See the block in main() for why this is written here and not left to the
# manifest: a manifest-only rule is satisfied again the moment somebody re-declines the row.
# `pit` is deliberately NOT here — The Pit is an area farm with no boss to picture.
REQUIRED_PORTRAITS = ("pindle",)


def read_boss_portrait_map():
    """v1642 — parse BOSS_PORTRAIT out of bible.html so the manifest and the APP can be compared.

    The hash check answers "are these the bytes a human opened?". It cannot answer "is the app
    still serving them?", and those are different questions: v1624 had ten correct portraits sitting
    in art/ and served an ITEM map instead. So this reads the real map. It is a deliberately dumb
    key:'file' scan of the one `var BOSS_PORTRAIT = { ... };` block — the block is hand-written and
    one entry per key, and a parser clever enough to handle anything else would also be clever
    enough to be wrong quietly. Returns {} if the block is not found, which the caller treats as a
    FAILURE rather than as a pass; a null result is never a passing result.
    """
    try:
        with open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        return {}
    i = src.find("var BOSS_PORTRAIT = {")
    if i < 0:
        return {}
    j = src.find("};", i)
    if j < 0:
        return {}
    block = src[i:j]
    # strip /* ... */ comments first: the block documents the refusals in prose that NAMES the very
    # ids and files we are looking for, and a comment describing a bug reads exactly like the bug.
    out, depth, k = [], 0, 0
    while k < len(block):
        if block.startswith("/*", k):
            depth += 1
            k += 2
        elif block.startswith("*/", k):
            depth -= 1
            k += 2
        else:
            if depth == 0:
                out.append(block[k])
            k += 1
    code = "".join(out)
    return dict(re.findall(r"(\w+)\s*:\s*'([^']+\.(?:png|jpg|gif))'", code))


def main(argv):
    with open(MANIFEST, encoding="utf-8") as fh:
        man = json.load(fh)
    rows = man["portraits"]
    quarantine = man.get("_quarantine", [])
    declined = [k for k in man.get("_declined", {}) if not k.startswith("_")]
    # v3899 #91 (REG-3962) - rows OPENED and pinned before bible.html serves them. Hashed exactly like portraits[],
    # and BOSS_PORTRAIT[bossId] may serve either the portraits[] file or this one, so wiring is one edit in bible.html.
    ready = list((man.get("_ready_to_wire") or {}).get("rows") or [])
    ready_by = dict((r["bossId"], r["file"]) for r in ready)

    if "--list" in argv:
        for r in rows:
            print("%-10s %-28s %s" % (r["bossId"], r["file"], r["depicts"]))
        for r in ready:
            print("%-10s %-28s %s" % ("READY:" + r["bossId"], r["file"], r["depicts"]))
        for q in quarantine:
            print("%-10s %-28s %s" % ("QUARANTINE", q["file"], q["depicts"]))
        for d in declined:
            print("%-10s %-28s %s" % ("DECLINED", "(level art)", man["_declined"][d][:110] + "..."))
        return 0

    bad = []
    for r in rows + ready:
        path = os.path.join(HERE, r["file"])
        if not os.path.exists(path):
            bad.append((r, "MISSING", "no file at art/%s — that thumbnail would 404" % r["file"]))
            continue
        got = sha256(path)
        if got != r["sha256"]:
            bad.append((r, "CHANGED", "sha256 %s..., manifest says %s..." % (got[:12], r["sha256"][:12])))

    for r, kind, detail in bad:
        print("%-8s %-10s %s" % (kind, r["bossId"], detail))
        print("         last human-verified content: %s" % r["depicts"])
    if bad:
        print("\n%d of %d portraits no longer match what a human verified." % (len(bad), len(rows) + len(ready)))
        print("OPEN each one and look at it. Do not re-bless a hash you have not seen the picture for.")
        return 1
    print("all %d boss portraits match the human-verified manifest (+%d opened and ready to wire)" % (len(rows), len(ready)))

    # ── v1642: the manifest and the APP must agree, and the refusals must stay refused ───────────
    served = read_boss_portrait_map()
    wrong = []
    if not served:
        wrong.append("could not read `var BOSS_PORTRAIT = {` out of bible.html — this check went "
                     "BLIND, which is a failure, not a pass")
    else:
        for r in rows:
            got = served.get(r["bossId"])
            if got != r["file"] and got != ready_by.get(r["bossId"]):
                wrong.append("BOSS_PORTRAIT[%s] serves %r but the verified manifest row is %r"
                             % (r["bossId"], got, r["file"]))
        quarantined = {q["file"] for q in quarantine}
        for r in ready:
            if r["file"] in quarantined:
                wrong.append("_ready_to_wire[%s] names QUARANTINED art %s" % (r["bossId"], r["file"]))
            if r["bossId"] not in {x["bossId"] for x in rows}:
                wrong.append("_ready_to_wire[%s] replaces no portraits[] row - a new boss id is pinned in portraits[] "
                             "with its wiring, not here" % r["bossId"])
        for bid, f in served.items():
            if f in quarantined:
                wrong.append("BOSS_PORTRAIT[%s] serves QUARANTINED art %s — that file was opened "
                             "and depicts nothing usable" % (bid, f))
        for d in declined:
            if d in served:
                wrong.append("BOSS_PORTRAIT[%s] now has a portrait (%s), but the manifest DECLINES "
                             "it with a written reason. If the reason is now wrong, OPEN the new "
                             "picture, move the row into 'portraits', and delete the _declined "
                             "entry — do not do one without the other." % (d, served[d]))
        # v1643 — CLOSE THE ESCAPE HATCH. Every check above is manifest-driven, so a portrait added
        # to bible.html and to NEITHER list was checked by nothing at all: not hashed, not opened,
        # not declined. That is the hole pindle would have fallen through — the wiring was the whole
        # point, and a silent pass is how it stays unwired.
        pinned = {r["bossId"] for r in rows}
        for bid, f in sorted(served.items()):
            if bid not in pinned and bid not in declined:
                wrong.append("BOSS_PORTRAIT[%s] serves %s but the manifest neither VERIFIES it "
                             "(portraits[]) nor DECLINES it (_declined) — nobody has opened this "
                             "picture. Open it, write what it depicts, and pin its sha256."
                             % (bid, f))
        # v1643 — pindle is REQUIRED, and the requirement is written down here rather than left to
        # the manifest alone. v1642 declared "no Pindleskin render exists in the repo" and moved on,
        # while bible.html's own name->art map had pointed "Pindleskin" at
        # art/reanimatedhorde-opt_graphic.png for weeks (a Reanimated Horde — his own monster class,
        # opened and confirmed). A purely manifest-driven check would go green again the moment
        # somebody moved that row back into _declined, which is exactly the regression to catch.
        for bid in REQUIRED_PORTRAITS:
            if bid not in pinned:
                wrong.append("%s MUST have a verified portrait row (REG-127): the art exists and "
                             "the app's own name->art map already used it. Declining it again is "
                             "the v1642 mistake, not a decision." % bid)
            elif bid not in served:
                wrong.append("%s has a verified manifest row but BOSS_PORTRAIT does not serve it — "
                             "the picture is pinned and the app still paints the level art." % bid)
    if wrong:
        print("")
        for w in wrong:
            print("MISMATCH  %s" % w)
        print("\nthe manifest and bible.html disagree. Two screens with different answers is worse "
              "than one wrong answer.")
        return 1
    print("BOSS_PORTRAIT in bible.html serves exactly those %d files; %d quarantined file(s) unused; "
          "%d declined id(s) still on level art (%s)"
          % (len(rows), len(quarantine), len(declined), ", ".join(declined)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
