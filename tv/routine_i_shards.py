# -*- coding: utf-8 -*-
"""Deal Routine I's fast Playwright specs by measured duration, not by file count.

--shard splits the file list into equal counts. On run 37139166700 that put 40.4 minutes of test
time on shard 6 and 24.9 on shard 2, so the slowest shard was the whole run. This deals largest-first
onto the lightest shard, the same way tv/shard_suite.py deals gate classes.

    python3 tv/routine_i_shards.py --shard 3 --of 6

prints that shard's paths, one per line, heaviest first. A file the table has not seen weighs the
median. An unreadable table still names every fast spec. An empty shard exits 2: Playwright with no
paths runs the whole project, which is the opposite of a shard.

The slow sims stay out. Their names are the chromium project's testIgnore in playwright.config.ts,
read from that file so a second copy cannot drift. Refresh the table from a run's blob zips:

    python3 tv/routine_i_shards.py --from-blobs <zip> [<zip> ...]
"""
import io
import json
import os
import re
import statistics
import sys
import zipfile

from console_safe import enable as _console_safe_enable
_console_safe_enable()

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TABLE = os.path.join(HERE, "routine_i_costs.json")
CONFIG = os.path.join(REPO, "playwright.config.ts")

# Playwright's default testMatch, written out: name.spec.ts and the cjs/mjs/jsx/tsx cousins.
_SPEC = re.compile(r"(?:^|/)[^/]*\.(?:spec|test)\.(?:[cm])?[jt]sx?$")


def chromium_test_ignore(config_text):
    """The chromium project's testIgnore, compiled. None when the config does not say."""
    i = (config_text or "").find("name: 'chromium'")
    if i < 0:
        return None
    m = re.search(r"testIgnore:\s*/(.+)/", config_text[i:i + 4000])
    if not m:
        return None
    try:
        return re.compile(m.group(1))
    except re.error:
        return None


def fast_specs(repo=None):
    """Every fast spec path, repo-relative, sorted. None when the ignore regex cannot be read."""
    repo = repo or REPO
    try:
        with io.open(os.path.join(repo, "playwright.config.ts"), encoding="utf-8") as fh:
            ignore = chromium_test_ignore(fh.read())
    except OSError:
        return None
    if ignore is None:
        return None
    root = os.path.join(repo, "tests")
    out = []
    for dirpath, _dirs, names in os.walk(root):
        for name in names:
            rel = os.path.relpath(os.path.join(dirpath, name), repo).replace("\\", "/")
            if not _SPEC.search("/" + rel):
                continue
            if ignore.search(rel):
                continue
            out.append(rel)
    return sorted(out)


def load_costs(path=None):
    """-> {path: seconds}. {} when the table is absent. None when it exists and will not read."""
    p = path or TABLE
    try:
        with io.open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print("routine_i_shards: %s exists but could not be read (%s) — every fast spec is still "
              "named, and the balance is unmeasured" % (os.path.basename(p), type(e).__name__),
              file=sys.stderr)
        return None
    costs = data.get("costs") if isinstance(data, dict) else None
    if not isinstance(costs, dict):
        print("routine_i_shards: %s has no costs object — balance is unmeasured" % os.path.basename(p),
              file=sys.stderr)
        return None
    return dict((k, float(v)) for k, v in costs.items())


#: v3891 (#194, his 11-09: "optimize the #194 all the way and make sure it keeps getting faster self improve it") - THE TABLE
#: REFRESHES ITSELF. tv/routine_i_costs.json was one hand snapshot (run 37139166700, edited 10-19) and the fast shards ran
#: 12.8-20.0 min on v3889's round. Each round's merge job now measures every spec from the blob reports and saves the table
#: (actions/cache); the next round's first job restores it, chooses the shard count from it and hands that ONE file to
#: every shard (ROUTINE_I_COSTS), so no two shards deal from different tables.
ENV_COSTS = "ROUTINE_I_COSTS"
#: playwright.config.ts's CI workers per shard: a shard's test wall is about its dealt seconds over this
WORKERS = 2
#: a fast shard's test wall may be at most this (setup - npm ci, the browser - comes on top, ~3 min)
TARGET_TEST_S = 8 * 60
MIN_SHARDS, MAX_SHARDS = 4, 60


def measured_costs(env=None):
    """The table every shard deals from: the committed one, with what the last round MEASURED (ROUTINE_I_COSTS) written
    over it file by file. -> {path: seconds} | None (the committed table will not read and nothing was measured)."""
    base = load_costs()
    p = (env if env is not None else os.environ).get(ENV_COSTS) or ""
    last = load_costs(p) if p and os.path.isfile(p) else None
    if not last:
        return base
    out = dict(base or {})
    out.update(last)
    return out


def choose_n(names, costs, target_s=TARGET_TEST_S, workers=WORKERS, n_min=MIN_SHARDS, n_max=MAX_SHARDS):
    """v3891 (#194) - the fewest fast shards whose heaviest dealt load, over the workers, fits target_s; when one file alone
    is over it (a file's tests run in one worker), the fewest that reach that floor. -> (n, why). Pure."""
    names = list(names)
    n_min, n_max = max(1, int(n_min)), max(1, int(n_max))
    if not names:
        return n_min, "no fast spec to deal"
    w = dict((n, file_weight(n, names, costs)) for n in names)

    def slowest(k):
        load = [0.0] * k
        for nm in sorted(names, key=lambda x: (-w[x], x)):
            i = min(range(k), key=lambda j: load[j])
            load[i] += w[nm]
        return max(max(load) / float(workers), max(w.values()))
    floor = max(w.values())
    aim = max(float(target_s), floor * 1.05)
    lo, hi = n_min, n_max
    if slowest(lo) <= aim:
        return lo, "%d shard(s) hold every fast spec inside the %d-s target" % (lo, target_s)
    if slowest(hi) > aim:
        return hi, "even %d shards model %d s - the round runs at %d" % (hi, slowest(hi), hi)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if slowest(mid) <= aim:
            hi = mid
        else:
            lo = mid
    return hi, ("%d shard(s) are the fewest whose heaviest models %d s (target %d s%s)"
                % (hi, slowest(hi), target_s, ", the heaviest file's own %d s is the floor" % floor if floor > target_s else ""))


def median_cost(names, costs):
    """The median measured cost of the files being dealt. 1.0 when nothing has been measured."""
    if not costs:
        return 1.0
    known = [float(costs[n]) for n in names if n in costs]
    if not known:
        known = [float(v) for v in costs.values()]
    if not known:
        return 1.0
    return float(statistics.median(known))


def file_weight(name, names, costs):
    """Seconds this file weighs. A file the table has not seen weighs the median, never zero."""
    med = median_cost(names, costs)
    if not costs or name not in costs:
        return float(med)
    v = float(costs[name])
    return v if v else 0.0


def deal(names, k, costs):
    """Largest-first onto the lightest shard. -> k lists (index 0 is shard 1). Empty lists stay,
    so shard K is always index K-1."""
    names = list(names)
    k = max(1, int(k))
    shards = [[] for _ in range(k)]
    load = [0.0] * k
    order = sorted(names, key=lambda n: (-file_weight(n, names, costs), n))
    for n in order:
        i = min(range(k), key=lambda j: (load[j], len(shards[j])))
        shards[i].append(n)
        load[i] += file_weight(n, names, costs)
    return shards


def costs_from_blob_zips(paths):
    """Sum every attempt's duration per spec, from Playwright blob report.jsonl files. -> {path: seconds}"""
    by_id = {}
    totals = {}

    def walk(node, file=None):
        loc = (node.get("location") or {}).get("file")
        if loc:
            file = loc
        if node.get("testId") and file:
            by_id[node["testId"]] = file
        for entry in node.get("entries") or []:
            walk(entry, file)
        for suite in node.get("suites") or []:
            walk(suite, file)

    for path in paths:
        by_id.clear()
        with zipfile.ZipFile(path) as zf:
            with zf.open("report.jsonl") as fh:
                for raw in fh:
                    if not raw.strip():
                        continue
                    event = json.loads(raw)
                    method = event.get("method")
                    if method == "onProject":
                        walk(event["params"]["project"])
                    elif method == "onTestEnd":
                        tid = event["params"]["test"]["testId"]
                        file = by_id.get(tid)
                        if not file:
                            continue
                        rel = file if file.startswith("tests/") else "tests/" + file.replace("\\", "/")
                        totals[rel] = totals.get(rel, 0.0) + float(event["params"]["result"]["duration"])
    return dict((k, round(v / 1000.0, 1)) for k, v in sorted(totals.items()))


def _opt(argv, name):
    """--name VALUE out of argv. -> (value | None, the rest)"""
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1], argv[:i] + argv[i + 2:]
    return None, argv


def main(argv):
    if argv and argv[0] == "--from-blobs":
        rest = argv[1:]
        out, rest = _opt(rest, "--out")      # v3891 (#194) - CI writes the round's table beside the cache, not the tree
        base_p, rest = _opt(rest, "--base")  # v3891 (#194) - the table this round dealt from: files it did not run keep it
        if not rest:
            print("usage: routine_i_shards.py --from-blobs [--out FILE] [--base FILE] <report.zip> [...]")
            return 2
        costs = costs_from_blob_zips(rest)
        if not costs:
            print("no spec durations in %s — nothing written" % (rest,))
            return 2
        kept = 0
        if base_p:
            base = load_costs(base_p) or {}
            kept = len(set(base) - set(costs))
            costs = dict(base, **costs)
        rec = {
            "source": "Playwright blob reports, chromium project, sum of every attempt duration",
            "files": len(costs),
            "totalSeconds": round(sum(costs.values()), 1),
            "costs": costs,
        }
        target = out or TABLE
        os.makedirs(os.path.dirname(os.path.abspath(target)) or ".", exist_ok=True)
        tmp = target + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        os.replace(tmp, target)
        print("wrote %s — %d files, %.0f s%s" % (target, len(costs), rec["totalSeconds"],
                                                (" (%d not run this round kept their last cost)" % kept) if kept else ""))
        return 0
    if argv and argv[0] == "--choose":
        # v3891 (#194) - the round's fast-shard count: n= and list= for the workflow's matrix; never fails the run
        rest = argv[1:]
        t, rest = _opt(rest, "--target-s")
        lo, rest = _opt(rest, "--min")
        hi, rest = _opt(rest, "--max")
        fb, rest = _opt(rest, "--fallback")
        outp, rest = _opt(rest, "--output")
        try:
            specs = fast_specs()
            if specs is None:
                raise ValueError("the chromium testIgnore could not be read")
            n, why = choose_n(specs, measured_costs() or {}, target_s=float(t) if t else TARGET_TEST_S,
                              n_min=int(lo) if lo else MIN_SHARDS, n_max=int(hi) if hi else MAX_SHARDS)
        except Exception as e:
            n, why = int(fb or 10), "the count could not be chosen (%s) - the round runs at the fallback" % e
        print("v3891 (#194) Routine I fast shards: %d - %s" % (n, why), file=sys.stderr)
        lines = "n=%d\nlist=%s\n" % (n, json.dumps(list(range(1, n + 1)), separators=(",", ":")))
        sys.stdout.write(lines)
        if outp:
            with io.open(outp, "a", encoding="utf-8") as fh:
                fh.write(lines)
        return 0
    shard = of = None
    i = 0
    while i < len(argv):
        if argv[i] == "--shard" and i + 1 < len(argv):
            shard = argv[i + 1]
            i += 2
        elif argv[i] == "--of" and i + 1 < len(argv):
            of = argv[i + 1]
            i += 2
        else:
            shard = None
            break
    if shard is None or of is None:
        print("usage: routine_i_shards.py --shard K --of N")
        return 2
    try:
        k = int(shard)
        n = int(of)
    except ValueError:
        print("shard and of must be integers")
        return 2
    if n < 1 or k < 1 or k > n:
        print("shard %s of %s is outside 1..N" % (shard, of))
        return 2
    specs = fast_specs()
    if specs is None:
        print("could not read the chromium testIgnore from playwright.config.ts — refusing to guess a file list")
        return 2
    costs = measured_costs()     # v3891 (#194) - the last round's measured table over the committed one
    chosen = deal(specs, n, costs)[k - 1]
    if not chosen:
        print("shard %s of %s dealt no files" % (shard, of))
        return 2
    for path in chosen:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
