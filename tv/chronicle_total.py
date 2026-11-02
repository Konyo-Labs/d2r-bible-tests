"""The Chronicle's own denominator, re-derived from the game files 2026-09-03.

⚠ THIS EXISTS BECAUSE THE ANSWER WAS LOST ONCE ALREADY. `bible.html` has carried this note for
months: *"One of the two is wrong by one entry, and neither can be re-derived on this machine right
now: the CASC extractor lives at /tmp/casc_extract and /tmp does not survive a reboot."* The
extractor SOURCE survived (it is `tv/casc_extract.c`, in this repo), and his 28 GB store survived.
The only thing that did not survive was the OUTPUT — the one thing anyone needed. So this file
records the measurement and the recipe, and no one has to rebuild CascLib to answer a question that
has now been answered twice.

⚠ THE GAME FILE ITSELF IS NOT COMMITTED. This repo is PUBLIC and `uniqueitems.txt` is Blizzard's
data. What is here is the arithmetic and how to reproduce it.

MEASURED, from `data:data/global/excel/uniqueitems.txt` pulled out of the live RotW CASC store:

      439  data rows in uniqueitems.txt
     -24   disableChronicle = 1   (Azurewrath, Constricting Ring, Gore Ripper,
                                   Zakarum's Salvation, Odium, ...)
     ----
      415  <- exactly what diablo2.io lists, and what a Google AI Overview echoed at him
     -12   further rows that are not spawnable
     ----
      403  spawnable AND in the Chronicle    <- THE GAME'S OWN CHRONICLE
      396  DISTINCT names among those 403
           Rainbow Facet occupies 8 rows, one per element -> 7 duplicate rows

So `chronTotal = 403` in bible.html is CORRECT and matches the game file exactly, and the in-game
panel reading of **404** recorded in that same comment was a misread. 415 is not wrong either — it
is 439 minus the 24 the game explicitly excludes from the Chronicle, which is a different question.

⚠ AN OPEN MEASUREMENT, NOT A DEFECT: the game has 396 DISTINCT Chronicle names while
`unique_roster.json` carries 398. Those count different things — the roster is built from the
page's own `_gUniqueRoster()`, which includes `_UNI_EXTRA` — and neither is claimed wrong here.
Anyone looking at that gap should start from the 8 Rainbow Facet rows.

HOW TO REPRODUCE (about ten minutes, needs the game installed):

    git clone --depth 1 https://github.com/ladislav-zezula/CascLib.git
    cd CascLib && mkdir build && cd build
    # current cmake refuses the project's own minimum without this
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 .. && make -j4
    # -Wl,-rpath or the binary cannot find its own framework at runtime
    g++ -O2 -std=c++17 -I<CascLib>/src -x c++ tv/casc_extract.c \\
        -F<CascLib>/build -framework casc -Wl,-rpath,<CascLib>/build -o casc_extract
    ./casc_extract "<D2R install>/Data" \\
        "data:data/global/excel/uniqueitems.txt" uniqueitems.txt
    python3 tv/chronicle_total.py --count uniqueitems.txt
"""
import io
import os
import sys

# What the extraction measured. A number here is EVIDENCE with a date on it, not a constant to
# compute from. bible.html's chronTotal stays this pin. The tally the surfaces divide by is that
# pin minus the six quest items, and route_totals plus window.d2rChronTotal are the readers.
MEASURED = {
    "when": "2026-09-03",
    "source": "data:data/global/excel/uniqueitems.txt, live RotW CASC store",
    "rows": 439,
    "disableChronicle": 24,
    "notSpawnable": 36,
    "chronicle": 403,
    "chronicleDistinctNames": 396,
    "duplicateRows": 7,
    "duplicateName": "Rainbow Facet",
    "diablo2ioListing": 415,
}


def count(path):
    """Re-derive the numbers above from an extracted uniqueitems.txt. -> dict

    Returns None for anything the file cannot answer rather than guessing — a column that has been
    renamed in a later patch must read as UNKNOWN, never as zero rows. [[unknown-stays-unknown]]
    """
    try:
        lines = [l for l in io.open(path, encoding="utf-8", errors="replace").read().split("\n")
                 if l.strip()]
    except Exception as e:
        return {"ok": False, "why": "could not read %s (%s)" % (path, str(e)[:60])}
    if len(lines) < 2:
        return {"ok": False, "why": "the file holds no data rows"}
    hdr = [c.strip().lower() for c in lines[0].split("\t")]
    idx = {c: i for i, c in enumerate(hdr)}
    for need in ("index", "spawnable", "disablechronicle"):
        if need not in idx:
            return {"ok": False,
                    "why": "column %r is absent — this is a different schema than the one measured "
                           "on %s, so the count is UNKNOWN rather than wrong"
                           % (need, MEASURED["when"])}
    rows = [l.split("\t") for l in lines[1:]]

    def g(r, c):
        i = idx.get(c)
        return (r[i].strip() if i is not None and i < len(r) else "")

    chron = [r for r in rows if g(r, "spawnable") == "1" and g(r, "disablechronicle") != "1"]
    names = [g(r, "index") for r in chron]
    return {"ok": True, "rows": len(rows),
            "disableChronicle": len([r for r in rows if g(r, "disablechronicle") == "1"]),
            "notSpawnable": len([r for r in rows if g(r, "spawnable") != "1"]),
            "chronicle": len(chron), "chronicleDistinctNames": len(set(names)),
            "duplicateRows": len(chron) - len(set(names))}


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    if len(sys.argv) > 2 and sys.argv[1] == "--count":
        d = count(sys.argv[2])
        if not d.get("ok"):
            print("REFUSED — %s" % d.get("why"))
            raise SystemExit(1)
        print("re-derived from %s:" % os.path.basename(sys.argv[2]))
        for k in ("rows", "disableChronicle", "notSpawnable", "chronicle",
                  "chronicleDistinctNames", "duplicateRows"):
            was, now = MEASURED.get(k), d.get(k)
            mark = "  " if was == now else "  ⚠ was %s" % was
            print("   %-24s %s%s" % (k, now, mark))
    else:
        print("MEASURED %s from %s" % (MEASURED["when"], MEASURED["source"]))
        for k in sorted(MEASURED):
            print("   %-24s %s" % (k, MEASURED[k]))
        print("\n   chronTotal in bible.html is 403 and the game agrees. The tally subtracts the")
        print("   six quest items. The 404 recorded in that file's comment was a misread.")
