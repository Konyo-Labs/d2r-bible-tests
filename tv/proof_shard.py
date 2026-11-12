# -*- coding: utf-8 -*-
"""REG-2585 / REG-2586 — ONE PROVE, MANY MACHINES: a proof-level shard plan, and the import that brings shards home.

⚠ WHY. A full `heart2 --prove` is ~3.5 h on his Mac (V1: 4,353 proofs). Per-proof keys cannot shrink the count (Phase 0
and 0b, /workspace notes: no design gets under ~1,900 re-proves), so the lever left is WALL TIME: the same proofs, on
many CI runners at once, banked into the verdict cache, then brought home.

THE PLAN (REG-2585). `heart2 --prove [names] --push --proof-shard K/N` proves only shard K's proofs. Every shard
computes the SAME plan from the same bytes: each gate's proofs are cut into contiguous chunks no costlier than about a
quarter of a shard's fair share (gate_costs.json prices one run of the gate; a chunk pays one clean run plus one run
per proof), and the chunks go, costliest first, to the least-loaded shard (ties to the lowest K). So a 41-proof
browser gate no longer sits on one runner for over an hour, and every (gate, proof) lands in EXACTLY ONE shard - a
proof in none is never proven, a proof in two is paid twice. The plan's digest names gate, index, the proof entry
itself and the shard, so shards cut from different names, bytes or N cannot pass as one set.

THE IMPORT (REG-2586). `heart2 --import-shards FILE...` merges the shards' banked PROVENs into this machine's verdict
cache, through the store's one locked writer, ALL OR NOTHING:
  · every shard 1..N is present exactly once, each FINISHED, all with one N and one plan digest;
  · every shard ran on THIS checkout's HEAD sha, from a clean tree (no tracked file differing from HEAD);
  · an entry is taken only if it is what peek() would serve: a dated, static, fact-free PROVEN - an ELSEWHERE, a
    BLIND, an UNPROVABLE, an undated or a traced entry is never banked;
  · an entry must belong to the shard that carries it (its gate and proof index are in that shard's plan) - a stray
    entry means the file is not what the shard wrote, and the import refuses;
  · the entry's `tree` is KEPT as the runner wrote it, never rewritten: #242's guard (_wave_gate) then still owes this
    tree one clean run of each gate before its imported proofs are reused here;
  · a key this machine already serves is kept as it is (its tree, its age) - an import never displaces a local proof.
Refused means nothing is written. [[unknown-stays-unknown]] [[inherited-claim-is-not-evidence]]
"""
import hashlib
import json
import math
import os
import re
import sys

if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from console_safe import enable as _console_safe_enable   # it prints non-ASCII; a cp1255 console must not crash
    _console_safe_enable()
except ImportError:                 # second eye: only a missing module is tolerated - a broken one is not hidden
    pass

#: a chunk is no costlier than this fraction of one shard's fair share, so the largest gates spread across shards
CHUNKS_PER_SHARD = 4
#: the version of the manifest a shard writes beside its entries; the import refuses any other
MANIFEST_V = 1
#: seconds one tampered run costs beyond the gate's own run (sandbox, tamper, restore, the verdict). MEASURED on the
#: box, 2026-10-23: 24 proofs of sub-second laws took 64 s on one lane; priced at the gate's run alone, a shard of
#: cheap laws looked 5x lighter than it ran
PROOF_OVERHEAD_S = 1.5
#: REG-2593 - what a proof costs ON A RUNNER, over what gate_costs + PROOF_OVERHEAD_S says. MEASURED on the 16-shard run
#: at dcff7160 (421 gates priced from their own provedAt gaps): median 0.42 (p10 0.11, p90 0.91) - a gate this file has
#: no measured row for is priced at that ratio, not at a desk guess.
#: REG-3243 - RE-MEASURED on v3867's 22-shard run at b398504d2 (2 provers a runner; 1,222 gates with both a gate cost and
#: their own provedAt gaps): median 0.62 (p25 0.36, p75 0.89). The 0.42 was two weeks and one prover count old, and
#: proof_costs.json priced 422 gates - every other gate rode this ratio, so v3867's plan modelled each shard at ~18 min
#: and they ran 18-55: shard 7 reached the 55-minute deadline with 6 proofs unstarted. proof_costs.json now prices 1,276.
#: v3881 (GitHub's round 3 on 4282aab10, shard 1: test_a_proof_shard_plan_is_balanced RED untampered) - RE-DERIVED: REG-3401
#: carries every measured price forward and raised the committed table, so the ratio moved under the constant - the
#: committed table's median is 0.703 (1,231 gates, p25 0.42, p75 1.01) and the round's own seed 0.741 (p25 0.45, p75 1.05);
#: 0.62 sat 0.121 from the seed, past the law's 0.1. 0.72 sits within 0.03 of both.
PROOF_COST_FACTOR = 0.72
#: v3883 (#129) - THE FACTOR IS DERIVED FROM THE TABLE THE ROUND PLANS WITH, AT PLAN TIME; the constant above is only the
#: fallback for a table too thin to give one. MEASURED: v3881 lost a GitHub round (4282aab10, shard 1) because REG-3401 moved
#: the committed table's median ratio to 0.703 and the round's own seed to 0.741 while this constant sat at 0.62 - a hand-set
#: number re-derived after each re-measure is a stale reading waiting for the next one. cost_factor() reads the median off the
#: very per-proof table plan() is handed (the committed one, or HEART2_SHARD_COSTS' seed), so the two cannot drift apart.
COST_FACTOR_MIN_ROWS = 50


def cost_factor(costs, per_proof, min_rows=None):
    """v3883 - what an unmeasured gate's proof is priced at, over its clean run + PROOF_OVERHEAD_S: the MEDIAN of
    per_proof[g] / (costs[g] + PROOF_OVERHEAD_S) over every gate the table measures both ways. Pure.
    -> (factor, rows) - rows under COST_FACTOR_MIN_ROWS gives (PROOF_COST_FACTOR, rows): too thin a table is not a measure"""
    need = COST_FACTOR_MIN_ROWS if min_rows is None else int(min_rows)
    cs, pp = dict(costs or {}), dict(per_proof or {})
    r = sorted(float(pp[g]) / (float(cs[g]) + PROOF_OVERHEAD_S) for g in pp
               if isinstance(pp.get(g), (int, float)) and pp[g] > 0 and isinstance(cs.get(g), (int, float)) and cs[g] > 0)
    if len(r) < max(1, need):
        return PROOF_COST_FACTOR, len(r)
    m = len(r) // 2
    return (r[m] if len(r) % 2 else (r[m - 1] + r[m]) / 2.0), len(r)
#: REG-2593 - the lanes one runner proves on (2 cores). A shard's wall is the larger of its work over its lanes and its
#: BROWSER work, which runs one gate at a time (#42 ONE BROWSER AT A TIME) - the old plan balanced only the first, and
#: its slowest shard ran 2.1x the mean
RUNNER_LANES = 2
#: REG-3211 - what one proof the verdict cache SERVES costs a shard: its key and a lookup, no law run. MEASURED on v3864's
#: Publish (run 42084305066, a commit ci/proof-keys-v3864 had already proved): shard 6 proved 380 of its 388 again (49.5
#: min) and shard 14 its 11 (23.5 min); slowest 3,170 s against a mean of 2,297 s. Once the exact commit's proofs are in the
#: seed (REG-3210) most of a plan is served, and a plan that priced a served proof like a run would pile the owed rest
#: wherever the names fell
SERVED_PROOF_S = 0.05
#: REG-3212 - a proof cut at its bound: neither PROVEN nor a defect of the law - UNKNOWN, owed, and named by the fan-in
TIMEOUT = "TIMEOUT"
#: REG-3401 - the prices a shard was planned on (HEART2_SHARD_COSTS), handed on beside its cache so the fan-in carries
#: every price the round did not re-measure into the next round's table
PREV_COSTS_NAME = "proof_costs.prev.json"
#: REG-3271 - the longest gap between two provedAt stamps of one gate that is still ONE proof's cost: the shard job's own
#: bound. MEASURED on v3872's set (0d4e24537): shard 14's store held 258 proofs of 10:0x-11:01 and one served from 04:21,
#: so that gate's "per-proof" gap read 6 hours; a gate of 2-3 proofs took it as its median and was priced at hours
MAX_PROOF_GAP_S = 75 * 60
#: REG-3272 - a shard's real prove time over the plan's work / lanes. MEASURED on v3872 (22 shards, every one of 9,378
#: proofs run fresh, 0 served): with the re-measured per-proof prices, real = 1.30 x modelled (fit through 0, residual
#: mean 154 s over 22 shards; the clean wave, the checkpoint writes and two lanes never perfectly busy are not in the
#: per-proof gaps). The plan's balance is unchanged by a common factor; the wall it SAYS, and its headroom, are not
SHARD_WALL_FACTOR = 1.30
#: v3891 (#194) - the factor a round MEASURES (real prove seconds over the plan's modelled wall, per shard, median) rides
#: the carried prices as "wallFactor" and the next plan uses it. It only ever RAISES the committed 1.30 (REG-3365's rule for
#: prices, held for the factor: under-planning costs a whole round at minute 55, over-planning a few idle minutes), and a
#: shard that modelled under this many seconds says nothing about the factor (setup noise outweighs its work)
WALL_FIT_MIN_MODEL_S = 120
#: v3894 - the words heart2 prints for a proof the run's deadline cut (REG-3212); a shard that says them is no wall sample
CUT_AT_BOUND = "cut at its bound"


def wall_factor(path=None, env=None):
    """v3891 (#194) - the wall factor the plan multiplies by: the carried table's measured "wallFactor" (HEART2_SHARD_COSTS)
    when it is higher than the committed SHARD_WALL_FACTOR, else that constant. -> float"""
    if path is None:
        path = (env if env is not None else os.environ).get("HEART2_SHARD_COSTS") or ""
    try:
        with open(path, encoding="utf-8") as fh:
            f = (json.load(fh) or {}).get("wallFactor")
        if isinstance(f, (int, float)) and not isinstance(f, bool) and f > SHARD_WALL_FACTOR:
            return float(min(f, 3.0))
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return SHARD_WALL_FACTOR


def fit_wall_factor(shard_dirs, current=None):
    """v3891 (#194) - what a round measured: each shard's real prove seconds (prove.log: "prove_seconds=") over the wall its
    plan modelled ("this shard's modelled wall N s", which already carries the factor it was planned with), median over
    the shards that modelled at least WALL_FIT_MIN_MODEL_S. -> the next factor (never below the committed one) | None
    when no shard says. current: the factor this round was planned with (its log's walls are scaled by it)."""
    cur = float(current or SHARD_WALL_FACTOR)
    ratios = []
    for d in shard_dirs or []:
        try:
            with open(os.path.join(d, "prove.log"), encoding="utf-8", errors="replace") as fh:
                log = fh.read()
        except OSError:
            continue
        m = re.search(r"this shard's modelled wall (\d+(?:\.\d+)?) s", log)
        r = re.search(r"prove_seconds=(\d+)", log)
        if not (m and r):
            continue
        # v3894 - a shard the deadline CUT measured the deadline, not its work. MEASURED 11-10: v3894's #92 rounds owed
        # every proof, every shard was cut at ~57 min, and their real/model ratios drove the carried factor to its 3.0 cap -
        # so the next plan over-modelled every shard 2.3x and a law reading the factor went red on GitHub
        if CUT_AT_BOUND in log:
            continue
        model, real = float(m.group(1)), float(r.group(1))
        if model >= WALL_FIT_MIN_MODEL_S and real > 0:
            ratios.append(real / model)
    if not ratios:
        return None
    ratios.sort()
    k = len(ratios) // 2
    med = ratios[k] if len(ratios) % 2 else (ratios[k - 1] + ratios[k]) / 2.0
    return round(max(SHARD_WALL_FACTOR, min(3.0, cur * med)), 3)
#: REG-3273 - the share of a shard's proving window (heart2 starts no proof past job minute 55) the plan's slowest shard
#: may fill. v3872's slowest shard needed 1.9x its modelled wall and the deadline cut 27 proofs; past this share the plan
#: says so in the shard's first lines, before a round is spent finding out
PLAN_HEADROOM = 0.70
#: the window those 55 minutes leave once a shard has set up (setup MEASURED 75-374 s on v3872's shards)
PROVE_WINDOW_S = 55 * 60 - 180
_SPEC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")


def parse_spec(spec):
    """'K/N' -> (k, n), 1 <= k <= n. Anything else raises ValueError (a shard nobody can read proves nothing)."""
    m = _SPEC.match(str(spec or ""))
    if not m:
        raise ValueError("a proof shard is K/N, e.g. 3/16 - got %r" % (spec,))
    k, n = int(m.group(1)), int(m.group(2))
    if not (1 <= k <= n):
        raise ValueError("a proof shard needs 1 <= K <= N - got %d/%d" % (k, n))
    return k, n


def _proof_key(pr):
    return json.dumps(pr, sort_keys=True, default=str)


def gate_costs(path=None):
    """{gate name: seconds per run} from gate_costs.json (run_gates' measured CI rows). -> dict ({} when absent), None
    when there and unreadable (REG-2597)"""
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate_costs.json")
    try:
        with open(path, encoding="utf-8") as fh:
            c = json.load(fh).get("costs") or {}
        return dict((str(k), float(v)) for k, v in c.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0)
    except FileNotFoundError:
        return {}                       # never measured: nothing to price from, the same fact as an empty file
    except (OSError, ValueError, TypeError, AttributeError):
        return None                     # REG-2597 - there and unreadable is UNKNOWN, never "no costs"



def _fill_timings(costs):
    """REG-3643 - unpriced proofs take their row from shard_timings.json (measured, or the median).
    A priced row is never lowered. An unreadable timings file is ignored (the plan already has a default)."""
    if not costs:
        return costs
    try:
        import shard_timings as ST
        extra = ST.per_proof()
    except Exception:
        return costs
    out = dict(costs)
    for g, v in extra.items():
        if g not in out and isinstance(v, (int, float)) and v > 0:
            out[g] = float(v)
    return out


def proof_costs(path=None, env=None):
    """REG-2593 - {gate: seconds per proof ON A RUNNER} from proof_costs.json (measure_costs' rows). -> dict ({} when
    absent: the plan then prices every gate from gate_costs, as it did), None when there and unreadable (REG-2597)

    REG-3274 - THE PRICES UPDATE THEMSELVES. With no `path`, HEART2_SHARD_COSTS names the costs the LAST round measured
    (the fan-in writes them beside the seed it saves; the seed job hands them to every shard in the one proof-seed
    artifact, so every shard reads the same file and cuts the same plan). Its rows win over tv/proof_costs.json's when
    they are HIGHER (REG-3365: never below the committed price); a gate it never measured keeps the committed price.
    Unreadable or absent: the committed file alone, as before."""
    if path is None:
        base = proof_costs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof_costs.json"))
        lp = (env if env is not None else os.environ).get("HEART2_SHARD_COSTS") or ""
        last = proof_costs(lp) if lp and os.path.isfile(lp) else None
        if base is None or not last:
            return _fill_timings(base)
        out = dict(base)
        # v3880 (REG-3365) - A ROUND'S PRICE MAY RAISE A GATE, NEVER SINK IT BELOW THE COMMITTED TABLE. MEASURED on v3878's
        # round: the last round had priced test_control at 19.1 s a proof (its proofs there were cheap - served, or
        # narrowed to the cases that caught them), the committed table says 272.8 s, and on shard 10 each proof took
        # 226-263 s. Priced at 19 s, 20 of its 28 owed proofs went to ONE shard (~80 min of proving in a 55-min job), and
        # the round needed four attempts. Pricing too high costs a few clean runs; pricing too low costs a whole round.
        for g, v in last.items():
            out[g] = max(v, base.get(g, 0.0))
        return _fill_timings(out)
    try:
        with open(path, encoding="utf-8") as fh:
            c = json.load(fh).get("perProof") or {}
        return dict((str(k), float(v)) for k, v in c.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0)
    except FileNotFoundError:
        return {}                       # never measured: nothing to price from, the same fact as an empty file
    except (OSError, ValueError, TypeError, AttributeError):
        return None                     # REG-2597 - there and unreadable is UNKNOWN, never "no costs"


def measure_costs(bodies):
    """REG-2593 - seconds per proof per gate, MEASURED from finished shard caches: within one shard a gate's proofs run
    back to back on one lane, so the gap between consecutive provedAt stamps is one proof's cost (its clean run is shared).
    Median over every gap of every shard. A gate with no gap (one proof per shard) is left out - priced by the factor.
    bodies: [cache body]. -> {gate: seconds}"""
    gaps = {}
    for body in bodies:
        per = {}
        for e in ((body or {}).get("entries") or {}).values():
            t = e.get("provedAt") if isinstance(e, dict) else None
            if isinstance(t, (int, float)) and not isinstance(t, bool) and e.get("gate"):
                per.setdefault(str(e["gate"]), []).append(t)
        for g, ts in per.items():
            ts.sort()
            # REG-3271 - a gap past the job's bound joins two rounds (a served proof beside a fresh one), never one proof
            gaps.setdefault(g, []).extend(x for x in ((b - a) / 1000.0 for a, b in zip(ts, ts[1:])) if x <= MAX_PROOF_GAP_S)
    out = {}
    for g, v in gaps.items():
        if v:
            v = sorted(v)
            m = len(v) // 2
            out[g] = round(v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2.0, 3)
    return out


#: v3881 (REG-3385) - heart2.CHECKPOINT_EVERY (#150): a shard runs one more clean run of a gate every this many of its proved
#: proofs. A copy - heart2 keys every proof, so the planner does not import it; test_a_chunk_never_outlasts_its_cut holds
#: the two equal. [[copy-drift]]
CHECKPOINT_EVERY = 4


def run_caps(names, env=None, gates=None):
    """v3880 (REG-3373) - {gate: the cut a proof shard applies to it, in seconds} for these gate names: the run's
    HEART2_GATE_CAP_S, raised by a gate's own larger prove_cap_s (REG-3317). {} when the run sets no cap (his Mac's push, a
    PC's census - nothing is cut there). The SAME rule heart2._gate_cap_for cuts by; test_a_chunk_never_outlasts_its_cut
    holds the two equal for every registered gate, so this copy cannot drift from the one that cuts. [[copy-drift]]"""
    env = os.environ if env is None else env
    try:
        run_cap = float(str(env.get("HEART2_GATE_CAP_S") or "").strip())
    except ValueError:
        run_cap = None          # heart2._prove_bounds' own rule: a value that is not a positive number is no bound
    if run_cap is None or not run_cap > 0:
        return {}
    own = {}
    try:
        if gates is None:
            import run_gates as _rg
            gates = getattr(_rg, "GATES", [])
        for g in gates:
            c = getattr(g, "prove_cap_s", None)
            if isinstance(c, (int, float)) and c > run_cap:
                own[getattr(g, "name", None)] = float(c)
    except Exception:
        pass
    return dict((str(nm), own.get(nm, run_cap)) for nm in names)


def plan(have, n, costs=None, browser=None, per_proof=None, lanes=RUNNER_LANES, served=None, report=None, caps=None,
         splits=None):
    """The shard every proof belongs to. -> {(gate, index): k} covering every proof of `have` exactly once (pure).

    have       [(name, filename, proofs)] as heart2.prove() holds them
    n          how many shards
    costs      {gate: seconds per run}; a gate it does not price costs the median of those it does (1.0 when none)
    browser    REG-2593: the gates proved one at a time (they start a browser). None: the pre-REG-2593 plan exactly
    per_proof  REG-2593: {gate: MEASURED seconds per proof on a runner}; a gate it lacks costs PROOF_COST_FACTOR x
               (its run + PROOF_OVERHEAD_S). A chunk of `size` proofs then costs per_proof x (size + 2): the proofs and
               the gate's two clean runs (the wave's and the closing one)
    lanes      a runner's lanes: a shard's wall is max(its work / lanes, its browser work)
    served     REG-3211: {(gate, index)} already PROVEN at this exact commit - the seed job's served.json, read the same
               by every shard (heart2._served_now). None: the plan as before REG-3211 exactly. Given, a served proof costs
               SERVED_PROOF_S and no clean run, and only the OWED proofs are cut by cost and spread longest-first - so
               the work still owed decides the shards, not where the names fall. Every proof is still assigned once:
               a served proof is served (copied into its shard's file) by the shard it belongs to
    report     REG-3211: a dict, filled with each shard's modelled wall and work (seconds) and the owed / served counts
    caps       v3880 (REG-3373): {gate: the cut its shard applies, seconds}; None reads run_caps() for these gates (the
               run's HEART2_GATE_CAP_S - none set, nothing changes). MEASURED on v3878 (run 42360263008): test_control
               [13]-[27] were ONE chunk (priced ~90 s/proof, real ~270 s) on a shard whose 1500 s cut ended it after ~4
               proofs a re-run (attempts 2-5 banked [4]-[7], [8]-[11], [13]-[17], then [13]-[16] again), so one law took
               6+ forty-minute attempts. Now no chunk is planned longer than its gate's cut (its proofs + the two clean runs),
               and two OWED chunks of one capped gate never share a shard while a shard without one is left (on one shard
               they run as one gate, under one cut). A gate whose ONE proof cannot fit is named in report["overCap"]."""
    n = int(n)
    if n < 1:
        raise ValueError("a plan needs at least one shard")
    costs = dict(costs or {})
    known = sorted(v for v in costs.values() if v > 0)
    default = known[len(known) // 2] if known else 1.0
    oh = PROOF_OVERHEAD_S
    pp = dict(per_proof or {})
    factor, _frows = cost_factor(costs, pp) if per_proof is not None else (PROOF_COST_FACTOR, 0)   # v3883
    if isinstance(report, dict):
        report["costFactor"] = {"factor": round(factor, 4), "rows": _frows,
                                "derived": per_proof is not None and _frows >= COST_FACTOR_MIN_ROWS}
    hit = set((str(g), i) for g, i in (served or ()))
    gates = []
    for name, _f, proofs in sorted(have, key=lambda t: str(t[0])):     # one order, whatever order the names came in
        p = len(proofs or [])
        if p:
            c = costs.get(str(name))
            c = c if (c is not None and c > 0) else default
            if per_proof is None:
                unit, fixed = c + oh, c                                 # every proof's run, and the gate's clean run
            else:
                u = pp.get(str(name))
                unit = u if u is not None else factor * (c + oh)
                fixed = 2 * unit
            owe = [i for i in range(p) if (str(name), i) not in hit]
            done = [i for i in range(p) if (str(name), i) in hit]
            gates.append((str(name), owe, done, unit, fixed, browser is not None and str(name) in browser))
    total = sum(u * len(o) + (f if o else 0.0) + SERVED_PROOF_S * len(d) for _n, o, d, u, f, _b in gates)
    target = total / float(n * CHUNKS_PER_SHARD) if total > 0 else 1.0
    # REG-2593, MODELLED on the measured costs: cutting browser gates finer made N=16 SLOWER (max 1675s vs 1349s): each
    # chunk pays its gate's two clean runs again. One target for every gate; the wall-aware placement below spreads them
    if caps is None:
        caps = run_caps([g[0] for g in gates])
    capd = dict((str(k_), float(v)) for k_, v in (caps or {}).items() if isinstance(v, (int, float)) and v > 0)
    # REG-3402 - a gate a round cut is planned in at least the chunks it learned (None: the committed and last-round tables)
    if splits is None:
        splits = proof_splits()
    spd = dict((str(k_), int(v)) for k_, v in (splits or {}).items() if isinstance(v, int) and v > 1)
    over = []
    owedkeys = set()
    chunks = []
    for name, owe, done, u, f, b in gates:
        p = len(owe)
        if p:
            k = max(1, min(p, int(math.ceil(u * p / target)) if target > 0 else 1))
            cap = capd.get(name)
            if cap and u > 0:                    # REG-3373 - never a chunk its shard's cut will end
                per = int((cap - f) // u)
                # v3881 (REG-3385) - AND COUNT THE CHECKPOINTS: heart2 runs one more clean run every CHECKPOINT_EVERY
                # proofs (#150), so a chunk of s proofs costs u*s + f + ((s - 1) // CHECKPOINT_EVERY) * u, not u*s + f.
                # MEASURED on v3879 shard 5: a 27-proof chunk ran 6 checkpoint clean runs the cut model never counted.
                while per > 1 and u * per + f + ((per - 1) // CHECKPOINT_EVERY) * u > cap:
                    per -= 1
                if per < 1:
                    per = 1
                    over.append(name)
                k = max(k, min(p, int(math.ceil(p / float(per)))))
            if spd.get(name):                    # REG-3402 - cut last round: split, whatever its price says
                k = max(k, min(p, spd[name]))
            base, extra = divmod(p, k)
            start = 0
            for j in range(k):
                size = base + (1 if j < extra else 0)
                idx = owe[start:start + size]
                start += size
                chunks.append((u * size + f, b, name, idx))
                owedkeys.add((name, idx[0]))        # REG-3373 - an OWED chunk (served ones run nothing)
        if done:        # REG-3211 - served: no run, no clean run, never the browser queue
            chunks.append((SERVED_PROOF_S * len(done), False, name, done))
    chunks.sort(key=lambda t: (-t[0], t[2], t[3][0]))
    tot = [0.0] * n
    brw = [0.0] * n
    lanes = max(1, int(lanes))
    out = {}
    held = {}
    for cost, b, name, idx in chunks:
        if browser is None:
            k = min(range(n), key=lambda s: (tot[s], s))
        else:   # REG-2593: the shard whose WALL grows least - its work over its lanes, or its browser queue
            k = min(range(n), key=lambda s: (max((tot[s] + cost) / lanes, brw[s] + (cost if b else 0.0)), tot[s], s))
        owed = (name, idx[0]) in owedkeys
        if owed and name in capd and k in held.get(name, ()):   # REG-3373 - never a second owed chunk of a capped gate
            free = [s for s in range(n) if s not in held[name]]   # on a shard holding one, while a shard without is left
            if free:
                k = min(free, key=lambda s: (tot[s], s) if browser is None
                        else (max((tot[s] + cost) / lanes, brw[s] + (cost if b else 0.0)), tot[s], s))
        if owed:
            held.setdefault(name, set()).add(k)
        tot[k] += cost
        if b:
            brw[k] += cost
        for i in idx:
            out[(name, i)] = k + 1
    if isinstance(report, dict):        # REG-3211 - what the plan expects of each shard, said by the run that cut it
        # REG-3272 - the wall a shard will REALLY take: the work over its lanes times the measured factor (v3891 #194: the
        # last round's, carried, when higher than the committed SHARD_WALL_FACTOR)
        _wf = wall_factor()
        report.update(wall=[round(_wf * max(t / lanes, w), 1) for t, w in zip(tot, brw)],
                      work=[round(t, 1) for t in tot], factor=_wf,
                      owed=sum(len(o) for _n, o, _d, _u, _f, _b in gates),
                      served=sum(len(d) for _n, _o, d, _u, _f, _b in gates), overCap=sorted(set(over)))
    return out


def plan_digest(have, n, assignment):
    """sha256 of every (gate, index, proof entry, shard) and N: shards from different plans never pass as one set."""
    rows = []
    for name, _f, proofs in have:
        for i, pr in enumerate(proofs or []):
            rows.append([str(name), i, _proof_key(pr), assignment.get((str(name), i))])
    rows.sort(key=lambda r: (r[0], r[1]))
    return hashlib.sha256(json.dumps({"n": int(n), "rows": rows}, sort_keys=True).encode("utf-8")).hexdigest()


def mine(assignment, k):
    """{gate: set(index)} - the proofs shard k proves."""
    out = {}
    for (name, i), s in assignment.items():
        if s == k:
            out.setdefault(name, set()).add(i)
    return out


def restrict_order(order, gates, own):
    """A push run's order cut down to one shard. -> (order, gates) with every gate that has no proof here dropped."""
    order2 = dict((g, [i for i in (order.get(g) or []) if i in own.get(g, ())]) for g in gates)
    gates2 = [g for g in gates if order2.get(g)]
    return dict((g, order2[g]) for g in gates2), gates2


def manifest(k, n, head, dirty, digest, own, names, stopped, at_ms, owed=None):
    """What a shard writes beside its entries when it FINISHES (an unfinished shard writes none). `owed` (REG-2591): every
    failure a shard that KEPT GOING found, [gate, index, verdict, reason] each."""
    return {"v": MANIFEST_V, "k": int(k), "n": int(n), "head": str(head or ""), "dirty": bool(dirty),
            "plan": str(digest), "finished": True, "names": sorted(names) if names else None,
            "stopped": list(stopped) if stopped else None, "at": int(at_ms),
            "owed": [list(f) for f in (owed or [])],
            "assigned": sorted([g, i] for g, idx in own.items() for i in idx)}


def servable(e):
    """THE SAME PREDICATE heart2._VerdictCache.peek() asks: a dated, static, fact-free PROVEN. -> bool"""
    if not isinstance(e, dict):
        return False
    t = e.get("provedAt")
    if not (isinstance(t, (int, float)) and not isinstance(t, bool)):
        return False
    if e.get("kind", "static") != "static" or "facts" in e or "factsRef" in e:
        return False
    return e.get("verdict") == "PROVEN"


def plan_rows(raw):
    """REG-2630 r2 - a manifest's `assigned` rows -> {(gate, index)}, or None when a row's index is not a whole number
    (a list or dict index would not even hash; a bool or text one names no proof). Rows of another shape are skipped."""
    out = set()
    for row in raw or []:
        if isinstance(row, list) and len(row) == 2:
            if type(row[1]) is not int:
                return None
            out.add((str(row[0]), row[1]))
    return out


def check_shards(bodies, head):
    """Is this a complete, consistent set of finished shards of HEAD? -> (ok, why | None, [(k, entries, assigned)])

    bodies  [(label, body | None, why-unreadable | None)] - each shard file as read
    head    this checkout's HEAD sha"""
    shards, ns, plans, owner = {}, set(), set(), {}
    for label, body, why in bodies:
        if body is None:
            return False, "%s is unreadable (%s)" % (label, why), []
        m = body.get("shard") if isinstance(body, dict) else None
        if not isinstance(m, dict) or m.get("v") != MANIFEST_V:
            return False, "%s carries no shard manifest - it is not a finished shard's file" % label, []
        if m.get("finished") is not True:
            return False, "%s is a shard that never finished" % label, []
        if not head or m.get("head") != head:
            return False, "%s ran on %s, not this checkout's HEAD %s" % (label, str(m.get("head"))[:12],
                                                                      str(head)[:12] or "UNKNOWN"), []
        if m.get("dirty") is not False:
            return False, "%s ran on a tree whose tracked files differed from its HEAD" % label, []
        k, n = m.get("k"), m.get("n")
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in (k, n)) or not 1 <= k <= n:
            return False, "%s names no readable shard number" % label, []
        if k in shards:
            return False, "shard %d/%d is given twice" % (k, n), []
        ns.add(n)
        plans.add(m.get("plan"))
        assigned = plan_rows(m.get("assigned"))
        if assigned is None:
            return False, "%s assigns a proof index that is not a whole number, so it names no proof" % label, []
        ent = body.get("entries")
        if not isinstance(ent, dict):
            return False, "%s has no 'entries' map" % label, []
        for row in assigned:
            if row in owner:
                return False, "%s[%s] is assigned to shards %d and %d - one plan gives a proof one shard" % (
                    row[0], row[1], owner[row], k), []
            owner[row] = k
        shards[k] = (ent, assigned)
    if not shards:
        return False, "no shard was given", []
    if len(ns) != 1:
        return False, "the shards disagree on N (%s)" % ", ".join(str(x) for x in sorted(ns)), []
    n = ns.pop()
    if len(plans) != 1:
        return False, "the shards were cut from different plans (other names, bytes or N)", []
    missing = sorted(set(range(1, n + 1)) - set(shards))
    if missing:
        return False, "shard(s) %s of %d are missing - a partial set is never imported" % (
            ", ".join(str(x) for x in missing), n), []
    if set(shards) - set(range(1, n + 1)):
        return False, "a shard number lies outside 1..%d" % n, []
    return True, None, [(k, shards[k][0], shards[k][1]) for k in sorted(shards)]


EXPORT_V = 1                               # REG-2630 - the manifest `heart2 --export-proved` writes beside its entries


def export_manifest(head, dirty, n, at_ms, runtime=None):
    """REG-2630 - what an export of one machine's banked PROVENs carries: the HEAD it was keyed at, whether that tree's
    tracked files differed from it, how many entries it holds, when it was written. REG-3044/3045 (#186): and the
    runtime it was proved under (platform, python major.minor, node major or "none"), as heart2.export_runtime()
    measured it - a field an older export lacks, which then reads UNKNOWN (EXPORT_V stays 1)."""
    m = {"v": EXPORT_V, "head": str(head or ""), "dirty": bool(dirty), "entries": int(n), "at": int(at_ms)}
    if isinstance(runtime, dict):
        for k in ("platform", "python", "node"):
            if runtime.get(k) is not None:
                m[k] = str(runtime[k])
    return m


# ══ #186 (REG-3044) - WHAT A PROOF ONE PC EARNED MAY SAY ON ANOTHER PC ═══════════════════════════════════════════════════
# A proof's key digests tracked bytes (heart2.key_for), so a PROVEN carried to another PC is re-keyed there and banked only
# over byte-identical inputs. But some proofs measure the PC, not the bytes: the capability a proof declares (heart2
# PROOF_NEEDS_HOST) says which. VENUE: the verdict read data no key holds - the game's install, his live console, his
# ledger, his reel shelf, one platform's font metrics - so another PC's proof of it is that PC's venue, never carried. OS:
# the verdict depends on the operating system - carried only when both platforms satisfy the need. TOOL: the verdict is a
# fact about the bytes wherever the tool runs - carried as any proof is, and served only where the tool is (REG-2715). A
# law holds every PROOF_NEEDS_HOST name in exactly one of the three, so a new capability cannot cross unclassified.
CARRY_VENUE = frozenset(("d2r-install", "live-console", "human-eyes-ledger", "reel-shelf", "overlap-venue"))
CARRY_OS = {
    "macos": lambda p: p == "darwin",
    "posix": lambda p: bool(p) and not p.startswith("win"),
    "posix-signals": lambda p: bool(p) and not p.startswith("win"),
    "windows": lambda p: bool(p) and p.startswith("win"),     # REG-3808 - the trace's ntpath wraps
}
#: v3895 (REG-3660) - the Claude CLI is a TOOL a PC has or lacks, like node: carried as a tool is
CARRY_TOOL = frozenset(("node", "bash", "numpy", "dir-link", "claude-cli"))


def carry_refusal(need, src_platform, here_platform):
    """REG-3044 - may a PROVEN proved on `src_platform` be banked on `here_platform`, given the capability its proof
    declares? `need` is THIS tree's declaration of that proof, never the file's word. -> None (it may) | why (it may not)"""
    if need is None or need == "":
        return None
    need = str(need)
    if need in CARRY_VENUE:
        return "it needs %s, which it measured on the PC that proved it, not on this one" % need
    if need in CARRY_OS:
        if not src_platform:
            return "it needs %s and the file does not say which platform proved it" % need
        if not (CARRY_OS[need](str(src_platform)) and CARRY_OS[need](str(here_platform or ""))):
            return "it needs %s: proved on %s, this PC is %s" % (need, src_platform, here_platform)
        return None
    if need in CARRY_TOOL:
        return None
    return "it declares %r, a capability the carry rule does not know" % need


def runtime_refusal(theirs, here):
    """REG-3045 (#186, D3) - may a CARRIED export be imported here at all, given the runtime each side proved under?
    -> None | why. Python major.minor must be recorded on both sides and equal; node is a major, "none" (measured absent)
    or unrecorded: unrecorded on either side refuses, two different majors refuse, and "none" on one side is an absence,
    not a version (a node proof is then ELSEWHERE wherever node is absent). UNKNOWN never passes."""
    t = theirs if isinstance(theirs, dict) else {}
    h = here if isinstance(here, dict) else {}
    for k, words in (("python", "Python"), ("node", "node")):
        if not t.get(k):
            return "the export does not record its %s, so whether it was proved under this PC's is UNKNOWN" % words
        if not h.get(k):
            return "this PC's %s could not be read, so whether the export matches it is UNKNOWN" % words
    if str(t["python"]) != str(h["python"]):
        return "it was proved under Python %s, this PC runs Python %s" % (t["python"], h["python"])
    if "none" not in (str(t["node"]), str(h["node"])) and str(t["node"]) != str(h["node"]):
        return "it was proved under node %s, this PC runs node %s" % (t["node"], h["node"])
    return None


def check_proved(bodies, head):
    """REG-2630 - files proved ELSEWHERE that `heart2 --import-proved` may take: a box export (`export` manifest) or any
    finished census shard (`shard` manifest), of THIS HEAD, from a tree that matched its HEAD. A partial census set is
    allowed here: every entry is still keyed by this checkout's bytes in select(), so a missing shard only means its
    proofs are proved by the push, never served unearned. -> (ok, why | None, [(i, entries, assigned)])"""
    out = []
    for i, (label, body, why) in enumerate(bodies or [], 1):
        if body is None:
            return False, "%s is unreadable (%s)" % (label, why), []
        ent = body.get("entries") if isinstance(body, dict) else None
        if not isinstance(ent, dict):
            return False, "%s has no 'entries' map" % label, []
        ex, sh = body.get("export"), body.get("shard")
        if isinstance(ex, dict) and sh is None:
            if ex.get("v") != EXPORT_V:
                return False, "%s carries an export manifest of another version (%r)" % (label, ex.get("v")), []
            m, assigned = ex, None
        elif isinstance(sh, dict) and ex is None:
            if sh.get("v") != MANIFEST_V:
                return False, "%s carries a shard manifest of another version (%r)" % (label, sh.get("v")), []
            done = sh.get("finished") is True
            if not done:
                return False, "%s is a shard that never finished" % label, []
            m, assigned = sh, plan_rows(sh.get("assigned"))
            if assigned is None:
                return False, "%s assigns a proof index that is not a whole number, so it names no proof" % label, []
        else:
            return False, "%s carries no export or shard manifest (or both) - nothing says where it was proved" % label, []
        if not head or head != m.get("head"):
            return False, "%s was keyed at %s, not this checkout's HEAD %s - prove the exact commit you push (bump it " \
                "first)" % (label, str(m.get("head"))[:12], str(head)[:12] or "UNKNOWN"), []
        if not (m.get("dirty") is False):
            return False, "%s was proved on a tree whose tracked files differed from its HEAD" % label, []
        if assigned is None:                 # an export has no plan: every entry it holds is its own claim
            assigned = set((str(e.get("gate")), e.get("proof")) for e in ent.values()
                           if isinstance(e, dict) and type(e.get("proof")) is int)   # REG-2630 - a list index never hashes
        out.append((i, ent, assigned))
    if not out:
        return False, "no file was given", []
    return True, None, out


#: REG-2630 - the tree an imported entry is banked under when its file claims THIS checkout's own tree id.
FOREIGN_TREE = "imported:claimed-this-tree"


def select(shards, keyer=None, dropped=None, here=None, refuse=None, refused=None):
    """The entries an import may bank. -> (ok, why | None, {key: entry}, skipped count)

    An entry outside its shard's plan refuses the whole import; one that is not servable is skipped (counted).
    keyer   (gate, proof index) -> the key THIS checkout's bytes give that proof (None: unkeyable here). A servable entry
            filed under any other key refuses the import: the shard's key is a claim, this tree's key is the fact.
    dropped REG-2596: a list -> such an entry is DROPPED instead (appended as (shard, gate, proof)) and never banked:
            a key this tree never gives can never be served here, so leaving it out costs nothing, and one law whose
            bytes differ on a runner no longer throws away the other 2,700 proofs. None -> the strict refusal.
    here    REG-2630 - THIS checkout's tree id. A file that claims an entry was proved HERE is not believed: the entry is
            banked under FOREIGN_TREE, so REG-2599 still owes this tree its clean run. None -> trees kept as written.
    A proof index that is not a whole number (a list, a dict, a bool, text) refuses the whole file: it names no proof.
    refuse  REG-3044: (file k, entry) -> why | None, asked of an entry that is servable and keyed here; a why leaves it
            out (appended to `refused` as (k, gate, proof, why)) - a proof of the other PC's venue, or of another OS."""
    take, skipped = {}, 0
    for k, ent, assigned in shards:
        for key, e in ent.items():
            if not isinstance(e, dict):
                skipped += 1
                continue
            if type(e.get("proof")) is not int:
                return False, "file %d holds %s with proof index %r - not a whole number, so it names no proof" % (
                    k, e.get("gate"), e.get("proof")), {}, 0
            if (str(e.get("gate")), e.get("proof")) not in assigned:
                return False, "shard %d holds %s[%s], a proof its plan never gave it" % (
                    k, e.get("gate"), e.get("proof")), {}, 0
            if not servable(e):
                skipped += 1                # ELSEWHERE, BLIND, UNPROVABLE, undated, traced: never banked
                continue
            if keyer is not None and keyer(str(e.get("gate")), e.get("proof")) != key:
                if dropped is not None:
                    dropped.append((k, str(e.get("gate")), e.get("proof")))
                    continue
                return False, "shard %d files %s[%s] under a key this checkout's bytes do not give it" % (
                    k, e.get("gate"), e.get("proof")), {}, 0
            if refuse is not None:
                _no = refuse(k, e)
                if _no:
                    if refused is not None:
                        refused.append((k, str(e.get("gate")), e.get("proof"), str(_no)))
                    continue
            if here is not None and e.get("tree") == here:
                e["tree"] = FOREIGN_TREE           # REG-2630 - "proved here" is this tree's word, never a file's (same dict: unbanked() asks `is`)
            take[key] = e                   # KEPT as the shard wrote it - its tree above all
    return True, None, take, skipped


def unbanked(shards, take):
    """REG-2586 - per shard, how many of its ASSIGNED proofs the import banks none for. -> {k: (unbanked, assigned)}

    A shard that stopped on a failure never ran what came after it; an assigned proof with no servable entry (never run,
    ELSEWHERE, BLIND...) is a proof the next push still pays for here."""
    out = {}
    for k, ent, assigned in shards:
        got = set((str(e.get("gate")), e.get("proof")) for key, e in (ent or {}).items()
                  if take.get(key) is e)
        out[k] = (len(set(assigned) - got), len(assigned))
    return out


def merge_into(disk_entries, take):
    """This machine's entries plus the imported ones; a key this machine already SERVES is kept. -> (entries, added)"""
    out = dict((k, v) for k, v in (disk_entries or {}).items() if isinstance(v, dict))
    added = 0
    for key, e in take.items():
        if servable(out.get(key)):
            continue
        out[key] = e
        added += 1
    return out, added


STORE_NAME = ".heart2_cache.json"          # the basename heart2's store writer accepts (heart2._StoreFile)


def fan_in(root, n, head, say=print):
    """REG-2588 — CI's fan-in: are the N shard artifacts under `root` (one dir per artifact, each holding the shard's
    STORE_NAME) one complete, importable set of HEAD? The SAME rules the import applies (check_shards, select), so a set
    the fan-in passes is a set `heart2 --import-shards` takes, and one it refuses is refused here first, on CI, where the
    log names the shard. -> exit code: 0 a whole set, 2 refused"""
    bodies, empty = [], []
    for d in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        path = os.path.join(root, d, STORE_NAME)
        if not os.path.isfile(path):
            empty.append(d)
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                body = json.load(fh)
            bodies.append((d, body if isinstance(body, dict) else None, None if isinstance(body, dict) else "not a map"))
        except (OSError, ValueError) as e:
            bodies.append((d, None, "%s: %s" % (type(e).__name__, str(e)[:80])))
    for d in empty:
        say("  ⚠ %s carries no %s - that shard banked nothing it could hand on" % (d, STORE_NAME))
    ok, why, shards = check_shards(bodies, head)
    if ok and empty:                                     # second eye: a dir with no store is not a shard of the set
        ok, why = False, "%d artifact dir(s) carry no %s (%s)" % (len(empty), STORE_NAME, ", ".join(empty[:4]))
    if ok:
        got = set(b["shard"].get("n") for _l, b, _w in bodies)
        if got != {n} or len(shards) != n:
            ok, why = False, "the workflow runs %d shards but the files name N=%s (%d given)" % (
                n, ",".join(str(x) for x in sorted(got, key=str)), len(shards))
    if ok:
        ok, why, take, skipped = select(shards)
    if not ok:
        say("  ✗ REG-2588 FAN-IN REFUSED: %s. This set would be refused by `heart2 --import-shards` too." % why)
        return 2
    owed = unbanked(shards, take)
    stops = dict((b["shard"]["k"], b["shard"].get("stopped")) for _l, b, _w in bodies if b["shard"].get("stopped"))
    fails = dict((b["shard"]["k"], b["shard"].get("owed")) for _l, b, _w in bodies if b["shard"].get("owed"))
    for k, _ent, assigned in shards:
        st = stops.get(k)
        say("    shard %2d/%d: %4d assigned, %4d banked%s%s" % (
            k, n, len(assigned), len(assigned) - owed[k][0],
            (", STOPPED at %s" % ("%s[%s] %s" % tuple(st[:3]) if isinstance(st, list) and len(st) >= 3 else st))
            if st else "",
            (", OWES %s" % ", ".join("%s[%s] %s" % tuple(f[:3]) for f in fails[k] if isinstance(f, list) and len(f) >= 3))
            if fails.get(k) else ""))
    _n_owed = sum(len(v) for v in fails.values())
    _n_unb = sum(u for u, _a in owed.values())
    cut = timeouts(fails)
    if cut:                             # REG-3212 - every proof cut at its bound, by name: UNKNOWN, never PROVEN
        say("  ⏱ REG-3212: %d proof(s) were cut at their bound - TIMEOUT, UNKNOWN, never PROVEN, owed: %s"
            % (len(cut), ", ".join("%s[%s] (shard %d)" % (g, i, k) for k, g, i in cut)))
    say("  ✓ REG-2588 FAN-IN: all %d shards of %s finished on one plan; %d PROVEN entr(ies) to import, %d not servable%s%s."
        % (n, str(head)[:12], len(take), skipped,
           (" - %d shard(s) STOPPED on a failure, owed a fix" % len(stops)) if stops else "",
           (" - REG-2591: %d failure(s) OWED a fix in %d shard(s)" % (_n_owed, len(fails))) if fails else ""))
    # REG-2594 - said out loud, never left to a reader to add up: what this set does NOT bank. Which of those the Mac
    # proves itself (ELSEWHERE here) only the Mac driver knows; it reports FULL or PARTIAL after its import
    say("  REG-2594: %d of %d assigned proof(s) bank nothing from this set (ELSEWHERE on a runner, owed, or never run)"
        % (_n_unb, sum(a for _u, a in owed.values())))
    return 0


def timeouts(fails):
    """REG-3212 - the proofs a shard's bound cut, from {shard k: owed rows}. -> sorted [(k, gate, index)]. Pure."""
    out = []
    for k, rows in (fails or {}).items():
        for f in rows or []:
            if isinstance(f, list) and len(f) >= 3 and f[2] == TIMEOUT:
                out.append((k, str(f[0]), f[1]))
    return sorted(out, key=lambda t: (t[1], str(t[2]), t[0]))


def _splits_in(path):
    """REG-3402 - the {gate: min chunks} a prices file carries ("split"). -> dict ({} when the file is absent or carries no
    split), None (UNKNOWN: the file is there and would not read - never "no split learned", which would plan a cut gate
    whole again)."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            sp = json.load(fh).get("split") or {}
        return dict((str(k), int(v)) for k, v in sp.items() if isinstance(v, int) and not isinstance(v, bool) and v > 1)
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def proof_splits(env=None):
    """REG-3402 - the least number of chunks each gate is planned in, learned from rounds that CUT it: the committed table's
    and the last round's (HEART2_SHARD_COSTS), the larger winning. -> {gate: k}. Read the same by every shard (one seed)."""
    out = _splits_in(os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof_costs.json"))
    if out is None:
        print("  ⚠ REG-3402: the committed proof_costs.json would not read - its learned splits are UNKNOWN this plan",
              file=sys.stderr)
        out = {}
    lp = (env if env is not None else os.environ).get("HEART2_SHARD_COSTS") or ""
    if lp and os.path.isfile(lp):
        got = _splits_in(lp)
        if got is None:
            print("  ⚠ REG-3402: the last round's prices file would not read - its learned splits are UNKNOWN this plan",
                  file=sys.stderr)
        for g, k in (got or {}).items():
            out[g] = max(out.get(g, 1), k)
    return out


def cut_splits(bodies, prev=None):
    """REG-3402 (his rule, 11-07 23:58: "we need to split the shard that DO TIME OUT that way they wont") - A GATE A ROUND CUT
    AT ITS DEADLINE IS SPLIT NEXT ROUND, whatever its price says. Its chunks this round = the shards it was assigned to; the
    next plan cuts it into at least twice that. A split once learned is carried (prev) and never forgotten; the larger wins.
    -> {gate: min chunks}. Pure."""
    out = dict((str(g), int(v)) for g, v in (prev or {}).items() if isinstance(v, int) and not isinstance(v, bool) and v > 1)
    on, cut = {}, set()
    for b in bodies or []:
        sh = (b or {}).get("shard") or {}
        for a in sh.get("assigned") or []:
            if isinstance(a, (list, tuple)) and a:
                on.setdefault(str(a[0]), set()).add(sh.get("k"))
        for f in sh.get("owed") or []:
            if isinstance(f, (list, tuple)) and len(f) >= 3 and f[2] == TIMEOUT:      # a row the bound cut
                cut.add(str(f[0]))
    for g in cut:
        out[g] = max(out.get(g, 1), 2 * max(1, len(on.get(g) or ())))
    return out


#: v3891 (#194, his 11-09: "optimize the #194 all the way and make sure it keeps getting faster self improve it") - THE ROUND
#: CHOOSES ITS OWN SHARD COUNT. A shard's prove step should model at most this many seconds; the seed job asks choose_n()
#: for the fewest shards whose slowest one fits, over the SAME inputs every shard plans from (the commit's proofs, the
#: carried prices, the served list). MEASURED on v3889's round (the old account): the slowest proof shard ran 43 min of a
#: 22-shard set while workers were never the wait. The repo is on KonyoDigital's Pro plan (~40 jobs at once, shared by every
#: workflow of a round - Konyo-Labs, tried 11-09, ran only 10), so the lever is a BALANCED count, never a wider one.
TARGET_PROVE_S = 12 * 60
#: the bounds a chosen count stays inside: never fewer than the old floor of a cold round's useful spread, never more than
#: today's 22 (his call 11-09: no workflow goes wider than it was - the Windows set, Playwright and the agent suites share
#: the same ~40 workers); a light round chooses fewer
MIN_SHARDS, MAX_SHARDS = 8, 22
#: past the floor (the costliest single chunk) a count within 5% of it is as fast as the round can be
FLOOR_SLACK = 1.05


def choose_n(have, n_min=MIN_SHARDS, n_max=MAX_SHARDS, target_s=TARGET_PROVE_S, **plan_kw):
    """v3891 (#194) - the fewest shards whose slowest MODELLED prove wall fits target_s. -> (n, info). Pure.

    plan_kw are plan()'s own (costs, browser, per_proof, lanes, served, caps, splits): the count is chosen by the very model
    every shard cuts its plan from, so the chooser and the shards cannot disagree about the work. info names the model's
    slowest wall at n, the owed/served counts and why n was chosen - a target that even n_max cannot meet says so and
    takes n_max (the round runs, wider, and the next round's measured prices correct the model)."""
    n_min, n_max = max(1, int(n_min)), max(1, int(n_max))
    if n_min > n_max:
        n_min = n_max
    cache = {}

    def slowest(n):
        if n not in cache:
            rep = {}
            plan(have, n, report=rep, **plan_kw)
            w = rep.get("wall") or [0.0]
            cache[n] = (float(max(w)), rep)
        return cache[n][0]
    # THE FLOOR. A chunk is never smaller than one proof plus its gate's two clean runs, so past some count more shards
    # cannot shorten the slowest - MEASURED cold on v3891's tree: 160 shards still modelled 1,064 s, one test_control
    # proof (~270 s) and its two clean runs x the wall factor. Past the floor a wider round only spends workers, so the
    # count aims at whichever is larger: the target, or the floor (with FLOOR_SLACK).
    floor = slowest(n_max)
    aim = max(float(target_s), floor * FLOOR_SLACK)
    lo, hi = n_min, n_max                  # slowest(hi) <= aim; find the smallest n that is
    if slowest(lo) <= aim:
        hi = lo
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if slowest(mid) <= aim:
            hi = mid
        else:
            lo = mid
    rep = cache[hi][1]
    if floor > target_s:
        # v3896 (REG-3675) - THE FLOOR IS THE SLOWEST SHARD AT THE MOST SHARDS, not "one chunk": MEASURED 11-11 on v3895's seed,
        # "the slowest proof chunk alone models 6343 s" read as one law to split, while the model's 22 shards were balanced
        # (every top shard the same wall) - the owed work spread as thin as the bound allows. Said as what it is.
        why = ("even at %d shards the slowest shard models %d s, over the %d-s target, so %d shard(s) are the fewest that "
               "reach that floor (%d s) - more would only spend workers" % (n_max, floor, target_s, hi, cache[hi][0]))
    else:
        why = "%d shard(s) are the fewest whose slowest models %d s, inside the %d-s target" % (hi, cache[hi][0], target_s)
    return hi, {"n": hi, "slowestModelS": round(cache[hi][0], 1), "targetS": target_s, "floorS": round(floor, 1),
                "owed": rep.get("owed"), "served": rep.get("served"), "why": why}


def headroom(wall, window=PROVE_WINDOW_S, share=PLAN_HEADROOM):
    """REG-3273 - the plan's slowest modelled wall against the proving window. -> (ok, sentence). Pure."""
    try:
        w = float(max(wall or [0]))
    except (TypeError, ValueError):
        return False, "the plan said no wall - its headroom is UNKNOWN"
    pct = 100.0 * w / float(window) if window else 0.0
    if w <= share * window:
        return True, "the slowest shard models %d s, %.0f%% of the %d-s proving window (at most %.0f%%)" % (
            w, pct, window, 100 * share)
    return False, ("⚠ REG-3273 the slowest shard models %d s, %.0f%% of the %d-s proving window - over the %.0f%% "
                   "headroom: its tail may be cut at minute 55 (TIMEOUT, owed); more shards or provers would fit it"
                   % (w, pct, window, 100 * share))


#: v3885 (#146, his 11-08: "i still dont understand why a full round when 23/24 shard pass only one red fails why does it need
#: too redo them all again" / "from now on the one shard that is red the other that were proved dont need to rerun only the red
#: failed shard") - the census's words for a law whose UNTAMPERED run went red (its clean run): on a first attempt that is a
#: measurement of the sandbox until it reds twice (v3884: show-toggle in round 3, the war-stash fill in round 4 - each green
#: locally and on the round before, nothing it reads changed)
CLEAN_RED = "ALREADY RED untampered"


def makeup_due(tot, killed=None, attempt=None):
    """REG-3270 - may a red proof round be made up by re-running its failed shards once? -> (due, why). Pure.

    Due only when the ONLY debt is proofs a bound cut (TIMEOUT): no law owes a fix, every shard left a readable store,
    and at least one proof was cut. A re-run shard serves everything its first attempt proved (the rerun seed, REG-3210)
    and runs only what the deadline cut. A law that went red, or a shard that left nothing, is never "made up" - those
    are a human's (or the next version's) to read.

    REG-3292 - `killed`: the shard numbers whose own job log says the RUNNER shut them down (tv/ship_when_green.py reads
    it); those may be made up too. A shard that left nothing for any other reason still is not."""
    if not isinstance(tot, dict):
        return False, "no census to read - not made up"
    cut, fix = tot.get("cut") or [], tot.get("fix") or []
    lost, missing = tot.get("lost") or [], tot.get("missing") or []
    if fix:
        # #146 - A LAW RED ONCE, UNTAMPERED, ON A RUN'S FIRST ATTEMPT IS RE-RUN ONCE - ONLY ITS SHARD, ON THE SAME SHA. Every
        # other shard keeps what it proved; a re-run shard serves what this run proved and runs only what it owes (REG-3210).
        # Never a proof that stayed green under sabotage, an anchor that matched nothing, a blind gate - those are code - and
        # never a second attempt: a law red twice on the same bytes is real.
        clean = [f for f in fix if len(f) > 3 and CLEAN_RED in str(f[3])]
        if attempt == 1 and len(clean) == len(fix):
            names = sorted(set("%s (shard %s)" % (f[0], f[4]) if len(f) > 4 else str(f[0]) for f in fix))
            return True, ("only %d law(s) red ONCE untampered on the run's first attempt: %s - a flake until it reds twice; "
                          "only its shard re-runs" % (len(fix), ", ".join(names)))
        if clean and attempt != 1 and len(clean) == len(fix):
            return False, "%d law(s) red untampered AGAIN on attempt %s - real: a fix, never another re-run" % (len(fix), attempt)
        return False, "%d proof(s) owe a fix (a law went red) - a re-run cannot make that up" % len(fix)
    # REG-3292 (REG-3085's case, parked since 10-29) - a shard the RUNNER killed leaves no store, through no fault of a
    # law (Publish 40812615686: "The runner has received a shutdown signal", exit 143, no manifest). Only a shard whose
    # own job log says so is made up; any other missing store stays UNKNOWN.
    killed = set(str(k) for k in (killed or ()))
    unexplained = [str(k) for k in lost if str(k) not in killed] + list(missing)
    if unexplained:
        return False, "%d shard(s) left no readable store - UNKNOWN, not made up" % len(unexplained)
    if not cut and not lost:
        return False, "nothing was cut at its bound"
    shards = sorted(set(str(f[4]) for f in cut if len(f) > 4))
    parts = []
    if cut:
        parts.append("%d proof(s) cut at their bound (TIMEOUT) on shard(s) %s" % (len(cut), ", ".join(shards)))
    if lost:
        parts.append("shard(s) %s killed by the runner (its log says so)" % ", ".join(sorted(str(k) for k in lost)))
    return True, "only " + " and ".join(parts) + " - a re-run proves just those"


def timeout_only_shards(tot):
    """v3881 (REG-3386) - the shards whose ONLY debt is proofs a bound cut, in a round that ALSO owes a fix elsewhere.
    -> sorted [shard number as str]; [] when nothing owes a fix (makeup_due then decides the whole run) or no census.

    MEASURED on v3879 (run 42387199487): shard 16 owed a fix (a law red untampered) and shard 5 owed only 6 TIMEOUT proofs.
    makeup_due refused the whole run - correctly, a red is a human's - so the cut shard waited on that human too, and both
    were re-run by hand. A cut shard is owed a re-run whatever the red shard's answer is: re-running it AT ONCE has its
    proofs done by the time the red is read. A shard that owes a fix, or left no store, is never in this list. Pure."""
    if not isinstance(tot, dict):
        return []
    cut, fix = tot.get("cut") or [], tot.get("fix") or []
    if not fix:
        return []
    red = set(str(f[4]) for f in fix if isinstance(f, (list, tuple)) and len(f) > 4)
    gone = set(str(k) for k in (tot.get("lost") or [])) | set(str(k) for k in (tot.get("missing") or []))
    part = set(str(f[4]) for f in cut if isinstance(f, (list, tuple)) and len(f) > 4) - red - gone
    return sorted(part, key=lambda k: (len(k), k))


#: v3881 (REG-3387) - the finisher (.github/workflows/proof-keys-finish.yml) re-runs a round at most after its first and
#: second attempts: a cut re-run serves everything already banked (REG-3210/3280), so each attempt only shrinks the debt, and
#: a third cut on one round is a human's to read, never an automatic loop.
FINISH_MAX_ATTEMPT = 2


def finish_plan(tot, attempt):
    """v3881 (REG-3387) - HIS ORDER 2026-11-07: "red is logical but timeout?" - a proof round whose debt includes proofs a
    bound CUT is finished on GitHub itself, never handed back as a failed round. -> {"action", "shards", "why"}. Pure.

    action  "rerun-failed": the ONLY debt is cut proofs, or a law red ONCE untampered on the first attempt (makeup_due, #146,
                            REG-3772) - re-run the run's failed jobs
            "rerun-jobs":   cut-only shards beside a shard that owes a fix (timeout_only_shards) - re-run just those jobs;
                            the red shard is never re-run (a red law is a human's, and re-running reds until green is a lie)
            "none":         nothing a re-run can finish, or this round was already finished FINISH_MAX_ATTEMPT times
    A shard that left no store is UNKNOWN here (no job log is read) - never made up by the finisher; the ship still may."""
    try:
        n = int(attempt)
    except (TypeError, ValueError):
        return {"action": "none", "shards": [], "why": "the run's attempt is unknown - nothing is re-run on a guess"}
    if n > FINISH_MAX_ATTEMPT:
        return {"action": "none", "shards": [],
                "why": "attempt %d: this round was already finished %d time(s) - what is left is a human's" % (n, n - 1)}
    if not isinstance(tot, dict):
        return {"action": "none", "shards": [], "why": "no census to read - UNKNOWN, nothing re-run"}
    # REG-3772 (#200, v3900's round 11-12) - the attempt goes to makeup_due, the ship's own rule (#146): asked with none, a law
    # red ONCE untampered on the first attempt read as "red AGAIN - real", so only cut shard 10 was re-run, the run became
    # attempt 2, and shards 11 and 14 (the war-stash flake) were left for a human. Now they are re-run with it, once.
    due, why = makeup_due(tot, attempt=n)
    if due:
        sh = sorted(set(str(f[4]) for f in ((tot.get("cut") or []) + (tot.get("fix") or []))
                        if isinstance(f, (list, tuple)) and len(f) > 4), key=lambda k: (len(k), k))
        return {"action": "rerun-failed", "shards": sh, "why": why}
    part = timeout_only_shards(tot)
    if part:
        return {"action": "rerun-jobs", "shards": part,
                "why": "shard(s) %s owe only cut proofs beside a red one - only those are re-run" % ", ".join(part)}
    return {"action": "none", "shards": [], "why": why}


def merge_shards(root, out, say=print):
    """REG-2961 (#161 stage 2) - THE SEED THE NEXT RUN RESTORES: every servable entry the shard files under `root` hold,
    in one heart2 store at `out` (no shard manifest - it is no shard's file). Read only by heart2's seed (HEART2_SHARD_SEED),
    which serves an entry only under the key the checkout's own bytes give it, so a seed of any age is safe; it is saved
    by actions/cache from main runs only. A key two files carry keeps the newer proof. -> exit code: 0 written, 2 none"""
    take, files = {}, 0
    for d in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        path = os.path.join(root, d, STORE_NAME)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                body = json.load(fh)
        except (OSError, ValueError) as e:
            say("  ⚠ REG-2961: %s is unreadable (%s) - left out of the seed" % (d, type(e).__name__))
            continue
        files += 1
        for key, e in ((body.get("entries") if isinstance(body, dict) else None) or {}).items():
            if not servable(e):          # what the import would bank, never more
                continue
            cur = take.get(key)
            if cur is None or e.get("provedAt") > cur.get("provedAt"):
                take[key] = e
    if not files:
        say("  ✗ REG-2961: no shard file under %s - nothing to seed the next run with" % root)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out + ".tmp", "w", encoding="utf-8") as fh:
        json.dump({"_why": "REG-2961 - PROVEN verdicts of one CI proof run, the next run's read-only seed; keyed by a digest "
                           "of every byte each proof depends on (tv/heart2.py _key)", "format": 2, "entries": take}, fh)
    os.replace(out + ".tmp", out)
    say("  ✓ REG-2961: %d PROVEN entr(ies) from %d shard file(s) -> %s" % (len(take), files, os.path.basename(out)))
    return 0


def _changed_paths(base, head):
    """REG-2962 - the repo paths that differ between two commits. -> set | None (no base, or git could not say)"""
    import subprocess
    if not base or not head:
        return None
    p = subprocess.run(["git", "-c", "core.quotePath=false", "diff", "--name-only", "-z", str(base), str(head)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return None
    return set(x for x in p.stdout.split("\0") if x)


def _gates_of(paths):
    """REG-2962 - the gates the hook proves for these changed paths (heart2.gates_for_tests: the hook's own rule); every
    gate when `paths` is None (UNKNOWN changes are judged as all of them). -> [name]"""
    import heart2 as _H
    if paths is None:
        return sorted(set(n for n, _f in _H.gate_files(say=lambda *a, **k: None)))
    return _H.gates_for_tests(sorted(p for p in paths if p.startswith("tv/test_") and p.endswith(".py")))


def _mac_only(names):
    """REG-2962 - of `names`, the gates the Mac proves and CI cannot bank (tv/proof_keys_mac.local_gates' rule). -> set"""
    import heart2 as _H
    import proof_keys_mac as _M
    files = dict(_H.gate_files(say=lambda *a, **k: None))
    have = [(n, files[n], _H.red_proofs_in(files[n]) or []) for n in names if n in files]
    along, unkeyable, _why = _M.local_gates(have, _H._tracked_files(), lambda *a: "keyed", _H.proof_needs_in)
    return set(along) | set(unkeyable)


def deploy_verdict(root, n, head, base, say=print, changed=None, gates_of=None, mac_only=None):
    """REG-2962 (#161 stage 2) - MAY THIS COMMIT PUBLISH? Every law the push changed since the last commit that published
    (`base`) must be PROVEN on CI, unless it is one only the Mac can prove (the hook proved it there).

    The proof set must be whole first (fan_in's rules); with no base, or a diff git cannot take, EVERY law is this push's
    (UNKNOWN is never "nothing changed"). A law is unproven when any shard OWES a failure on it (REG-2591: a shard that
    keeps going names every failure it found) - whatever its other proofs say. A law owed a fix that this push did not
    change is said and never holds the deploy: the hook never proved unchanged laws either. -> 0 publish, 1 held, 2 refused"""
    gates_of = gates_of or _gates_of
    mac_only = mac_only or _mac_only
    bodies = []
    for d in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        path = os.path.join(root, d, STORE_NAME)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                body = json.load(fh)
            bodies.append((d, body if isinstance(body, dict) else None, None if isinstance(body, dict) else "not a map"))
        except (OSError, ValueError) as e:
            bodies.append((d, None, type(e).__name__))
    ok, why, shards = check_shards(bodies, head)
    if ok and len(shards) != int(n):
        ok, why = False, "%d of %d shards" % (len(shards), int(n))
    if not ok:
        say("  ✗ REG-2962 DEPLOY HELD: the proof set is not whole (%s) - this push's laws are UNPROVEN on CI" % why)
        return 2
    if changed is None:
        changed = _changed_paths(base, head)
    names = gates_of(changed)
    local = mac_only(names) if names else set()
    mine = sorted(set(names) - set(local))
    _text, tot = census(root, head, n)
    owed = {}
    for f in tot["fix"] + tot["cut"]:   # REG-3212 - a TIMEOUT on one of this push's laws holds the deploy too: UNPROVEN
        owed.setdefault(str(f[0]), []).append(f)
    held = [g for g in mine if g in owed]
    scope = ("the %d law(s) this push changed since %s" % (len(names), str(base)[:12])) if changed is not None else (
        "EVERY law (%d) - the last published commit is unknown or git could not diff it, so every law is this push's"
        % len(names))
    if local:
        say("  REG-2962: %d of them only the Mac can prove (the hook proved them there): %s"
            % (len(local), ", ".join(sorted(local)[:12])))
    others = sorted(set(owed) - set(held))
    if others:
        say("  REG-2962: %d law(s) this push did NOT change are owed a fix on CI (the census lists them); they do not hold "
            "this deploy: %s" % (len(others), ", ".join(others[:12])))
    if held:
        say("  ✗ REG-2962 DEPLOY HELD: %d law(s) of %s are owed on CI (a fix, or a proof its bound cut - TIMEOUT):"
            % (len(held), scope))
        for g in held:
            for f in owed[g]:
                say("     %s[%s] %s - %s (shard %s)" % (f[0], f[1], f[2], str(f[3])[:140], f[4]))
        return 1
    say("  ✓ REG-2962: %s - %d proved on CI, none owed a fix. The deploy may go." % (scope, len(mine)))
    return 0


def census(root, head=None, n=None):
    """REG-2595 - the post-push CENSUS of one 16-shard run: what each shard proved, and which laws the next batch must
    fix. Never a gate: it reads whatever the shards left (a missing or broken store is named, never fatal).
    -> (markdown text, {"assigned", "proven", "owed", "unbanked", "fix": [[gate, idx, verdict, why, shard]]})"""
    rows, fix, cut, walls, unb, missing = [], [], [], [], {}, []
    for d in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        body = None
        try:
            with open(os.path.join(root, d, STORE_NAME), encoding="utf-8") as fh:
                body = json.load(fh)
        except (OSError, ValueError):
            pass
        try:
            with open(os.path.join(root, d, "prove.log"), encoding="utf-8", errors="replace") as fh:
                m = re.findall(r"prove_seconds=(\d+)", fh.read())
            if m:
                walls.append(int(m[-1]))
        except OSError:
            pass
        sh = (body or {}).get("shard") if isinstance(body, dict) else None
        if not isinstance(sh, dict):
            missing.append(d)
            continue
        try:                            # second eye: one malformed store is named, never the end of the census
            asg = set((str(g), int(i)) for g, i in (sh.get("assigned") or []))
            got = set((str(e.get("gate")), int(e.get("proof"))) for e in ((body.get("entries") or {}).values())
                      if isinstance(e, dict) and e.get("verdict") == "PROVEN")
            bad = [list(f[:4]) for f in (sh.get("owed") or [])]      # REG-2591: every failure a kept-going shard owes
            if sh.get("stopped") and list(sh["stopped"][:2]) not in [f[:2] for f in bad]:
                bad.append(list(sh["stopped"][:4]))                     # a fail-fast shard's stop, never dropped
            bad = [(f + ["?"] * 4)[:4] for f in bad]
            bad = [[str(f[0]), f[1], str(f[2]), str(f[3])] for f in bad]
        except (TypeError, ValueError, KeyError, AttributeError):
            missing.append(d + " (unreadable store)")
            continue
        for f in bad:
            # REG-3212 (the second eye on v3865) - a proof cut at its bound is owed, but it is no defect of its law: it is
            # listed apart, never under "laws owed a fix" (a law that only ran out of time read as one to repair)
            (cut if f[2] == TIMEOUT else fix).append(f + [sh.get("k")])
        failed = set((str(f[0]), f[1]) for f in bad)
        for g, i in asg - got - failed:
            unb[g] = unb.get(g, 0) + 1
        rows.append((sh.get("k"), len(asg), len(asg & got), len(bad), str(sh.get("head") or "")[:12]))
    heads = sorted(set(r[4] for r in rows))
    ks = set(r[0] for r in rows)
    lost = [k for k in range(1, int(n) + 1) if k not in ks] if n else []
    _order = lambda f: (str(f[0]), f[1] if isinstance(f[1], int) else 0)      # noqa: E731
    tot = dict(assigned=sum(r[1] for r in rows), proven=sum(r[2] for r in rows), owed=len(fix),
               unbanked=sum(unb.values()), fix=sorted(fix, key=_order), cut=sorted(cut, key=_order),
               lost=lost, missing=missing, stores=len(rows))      # REG-3270 - what makeup_due reads
    out = ["## Proof census at %s" % (", ".join(heads) or "(no shard store)"), ""]
    if head and heads and heads != [str(head)[:12]]:
        out += ["⚠ the shards ran on %s, not %s" % (", ".join(heads), str(head)[:12]), ""]
    out.append("%d shard store(s)%s. Assigned %d proof(s): PROVEN %d · owed a fix %d · unbanked %d (ELSEWHERE on a "
               "runner, or never run)%s." % (len(rows), (" - %d dir(s) carry none: %s" % (len(missing), ", ".join(missing[:6])))
                                            if missing else "", tot["assigned"], tot["proven"], tot["owed"], tot["unbanked"],
                                            (" · cut at the bound %d (TIMEOUT - owed to the next round, not a fix)"
                                             % len(tot["cut"])) if tot["cut"] else ""))
    if lost:
        out.append("⚠ %d of %d shard(s) left no readable store: %s - their laws are UNKNOWN, not green." % (
            len(lost), int(n), ", ".join(str(k) for k in lost)))
    _cut = tot["cut"]
    if _cut:                            # REG-3212 - a bound cut them: UNKNOWN, not a defect of the law, never PROVEN
        out.append("⏱ %d proof(s) were cut at their bound (TIMEOUT - UNKNOWN, never PROVEN; owed to the next round, not a "
                   "fix): %s." % (len(_cut), ", ".join("%s[%s] (shard %s)" % (f[0], f[1], f[4]) for f in _cut)))
    if walls:
        mean = sum(walls) / float(len(walls))
        out.append("Shard prove walls: slowest %d s, mean %.0f s (%.2fx)." % (max(walls), mean, max(walls) / mean if mean else 0))
    out += ["", "### Next batch - laws owed a fix (%d)" % len(fix)]
    if fix:
        out += ["", "| law | proof | verdict | why | shard |", "|---|---|---|---|---|"]
        cell = lambda v: " ".join(str(v).replace("|", "/").split())
        out += ["| %s | %s | %s | %s | %s |" % (cell(f[0]), cell(f[1]), cell(f[2]), cell(f[3])[:120], cell(f[4]))
                for f in tot["fix"]]
    elif missing or lost or not rows:
        out.append("None listed - but %s, so this is NOT a clean bill." % (
            "no shard store was read" if not rows else "some shards left no readable store"))
    else:
        out.append("None: every assigned proof that ran is PROVEN.")
    if unb:
        out += ["", "### Unbanked by law (top 20 of %d)" % len(unb), ""]
        out += ["- %s: %d" % (g, c) for g, c in sorted(unb.items(), key=lambda kv: (-kv[1], kv[0]))[:20]]
    return "\n".join(out) + "\n", tot


def bank(root, out, say=print):
    """v3862 (REG-3155) - the proof bank's bundle: ONLY each shard dir's STORE_NAME, as proof-shard-<k>/STORE_NAME, in one
    .tgz at `out` - what tv/proof_release.safe_extract takes and nothing it would refuse. Built in the fan-in (read-only),
    so the one job that may write runs no repo code and no workflow names the cache file. -> exit 0 packed, 2 nothing"""
    import tarfile
    members = []
    for d in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        p = os.path.join(root, d, STORE_NAME)
        if os.path.isfile(p) and not os.path.islink(p):
            members.append((p, d + "/" + STORE_NAME))
    if not members:
        say("  ✗ no shard store under %s - nothing to bank" % root)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with tarfile.open(out, "w:gz") as tf:
        for p, arc in members:
            tf.add(p, arcname=arc, recursive=False)
    say("  REG-3155: %d shard store(s) packed into %s (%d bytes)" % (len(members), os.path.basename(out), os.path.getsize(out)))
    return 0


def main(argv=None):
    import argparse
    import subprocess
    ap = argparse.ArgumentParser(description="REG-2588 - the CI fan-in check over N proof-shard artifacts")
    ap.add_argument("--fan-in", dest="root", default=None, help="dir holding one sub-dir per shard artifact")
    ap.add_argument("--shards", type=int, default=None, help="N, the workflow's shard count")
    ap.add_argument("--head", default=None, help="the sha the shards must have run on (default: git rev-parse HEAD)")
    ap.add_argument("--measure-costs", dest="measure", default=None,
                    help="REG-2593: dir of finished shard artifacts -> write proof_costs.json (seconds per proof)")
    ap.add_argument("--census", default=None, help="REG-2595: dir of shard artifacts -> the post-push census (markdown)")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="REG-3270: with --census, also write its totals as JSON (what tv/ship_when_green.py's make-up reads)")
    ap.add_argument("--out", default=None, help="with --census: also write the census to this file; with --merge-shards: "
                                                "the seed file")
    ap.add_argument("--merge-shards", dest="merge", default=None,
                    help="REG-2961: dir of shard artifacts -> one seed store (--out) for the next run's shards")
    ap.add_argument("--deploy-verdict", dest="verdict", default=None,
                    help="REG-2962: dir of shard artifacts -> may this commit publish (with --shards, --head, --base)")
    ap.add_argument("--base", default=None, help="with --deploy-verdict: the last commit that published (empty: UNKNOWN)")
    ap.add_argument("--bank", default=None, help="v3862: dir of shard artifacts -> one proof-bank bundle (--out FILE.tgz)")
    ap.add_argument("--finish-plan", dest="finish", default=None,
                    help="v3881 (REG-3387): a round's census.json -> what the finisher re-runs (JSON on stdout, or --out)")
    ap.add_argument("--attempt", default=None, help="with --finish-plan: the run attempt that just completed")
    a = ap.parse_args(argv)
    if a.finish is not None:
        try:
            with open(a.finish, encoding="utf-8") as fh:
                tot = json.load(fh)
        except (OSError, ValueError):
            tot = None
        plan_ = finish_plan(tot, a.attempt)
        text = json.dumps(plan_, ensure_ascii=False)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
        print(text)
        return 0
    if a.bank:
        if not a.out:
            ap.error("--bank needs --out FILE")
        return bank(a.bank, a.out)
    if a.merge:
        if not a.out:
            ap.error("--merge-shards needs --out FILE")
        return merge_shards(a.merge, a.out)
    if a.verdict:
        if a.shards is None:
            ap.error("--deploy-verdict needs --shards N")
        head = a.head
        if not head:
            p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, encoding="utf-8",
                               errors="replace")
            head = p.stdout.strip() if p.returncode == 0 else ""
        return deploy_verdict(a.verdict, a.shards, head, (a.base or "").strip() or None)
    if a.census:
        text, _t = census(a.census, a.head, a.shards)
        print(text)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(text)
        if a.json_out:                  # REG-3270 - the totals, for the make-up decision on the Mac
            _due, _why = makeup_due(_t)
            with open(a.json_out, "w", encoding="utf-8") as fh:
                json.dump(dict(_t, head=a.head, n=a.shards, makeupDue=_due, makeupWhy=_why), fh, ensure_ascii=False)
        return 0                        # a census informs the next batch; it never gates a push
    if a.measure:
        bodies = []
        for d in sorted(os.listdir(a.measure)):
            f = os.path.join(a.measure, d, STORE_NAME)
            if os.path.isfile(f):
                with open(f, encoding="utf-8") as fh:
                    bodies.append(json.load(fh))
        got = measure_costs(bodies)
        # REG-3401 (his "if this shard times out again ... make sure it doesnt happen", 11-07) - A PRICE ONCE MEASURED IS NEVER
        # FORGOTTEN. Each round saved ONLY what it re-measured, so a gate a round SERVED from the bank lost its measured
        # price and the next plan fell back to the committed table. MEASURED on v3880's round (6f20c0cb2): test_a_safety_
        # net_red_closes_only_its_own_lock was planned at 10.4 s a proof (v3872's table) and cost 57.5 s - 27 proofs, ~21
        # min unplanned, all on shard 5, and its last 9 were cut at minute 55. Every shard hands on the prices it was planned
        # on (PREV_COSTS_NAME, beside its cache); the round's saved table is those prices, with what this round measured
        # written over them.
        prev = {}
        for d in sorted(os.listdir(a.measure)):
            pf = os.path.join(a.measure, d, PREV_COSTS_NAME)
            if os.path.isfile(pf):
                pv = proof_costs(pf)
                if pv:
                    prev = pv
                    break
        if not got and not prev:        # second eye: an empty or wrong dir never blanks the table the plan reads
            print("  ✗ REG-2593: no shard cache under that dir priced any gate - proof_costs.json is left as it was")
            return 2
        carried = len(set(prev) - set(got))
        got = dict(prev, **got)
        prev_split = {}
        for d in sorted(os.listdir(a.measure)):
            pf = os.path.join(a.measure, d, PREV_COSTS_NAME)
            if os.path.isfile(pf):
                prev_split = _splits_in(pf)
                if prev_split is None:
                    print("  ⚠ REG-3402: %s would not read - the splits it carried are UNKNOWN, not carried" % pf)
                break
        split = cut_splits(bodies, prev_split)     # REG-3402 - what this round cut is split next round
        # REG-3274 - --out: the round's own prices, saved beside the next seed (the committed table is left as it is)
        out = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof_costs.json")
        heads = sorted(set(str(((b or {}).get("shard") or {}).get("head") or "")[:12] for b in bodies))
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        # v3891 (#194) - and the wall factor this round MEASURED (real prove seconds over modelled, per shard), never below
        # the one it was planned with: the next plan's walls - and the seed's chosen count - start from it
        _dirs = [os.path.join(a.measure, d) for d in sorted(os.listdir(a.measure))
                 if os.path.isdir(os.path.join(a.measure, d))]
        _cur = SHARD_WALL_FACTOR
        for d in _dirs:
            pf = os.path.join(d, PREV_COSTS_NAME)
            if os.path.isfile(pf):
                _cur = wall_factor(pf)
                break
        _fit = fit_wall_factor(_dirs, current=_cur)
        _wf_next = max(_cur, _fit) if _fit is not None else _cur
        print("  v3891 (#194) WALL FACTOR: planned with %.3f, this round measured %s -> the next round plans with %.3f"
              % (_cur, ("%.3f" % _fit) if _fit is not None else "nothing (no shard modelled enough to say)", _wf_next))
        with open(out + ".tmp", "w", encoding="utf-8") as fh:
            json.dump({"v": 1, "measuredOn": "a GitHub runner, %d shard(s) at %s" % (len(bodies), ",".join(heads)),
                       "perProof": dict(sorted(got.items())), "split": dict(sorted(split.items())),
                       "wallFactor": _wf_next}, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(out + ".tmp", out)
        print("  REG-2593: %d gate(s) priced from %d shard cache(s) -> %s (REG-3401: %d carried from the prices this round "
              "was planned on)" % (len(got), len(bodies), a.out or "tv/proof_costs.json", carried))
        return 0
    if not a.root or a.shards is None:
        ap.error("--fan-in DIR and --shards N are required (or --measure-costs DIR)")
    head = a.head
    if head is None:
        p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        head = p.stdout.strip() if p.returncode == 0 else ""
    return fan_in(a.root, a.shards, head)


if __name__ == "__main__":
    raise SystemExit(main())
