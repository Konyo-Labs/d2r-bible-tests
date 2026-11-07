"""#107 one-off probe: run each law GitHub's Windows prover found red untampered, and keep why.

python .github/win107_probe.py <chunk> <of> <outdir> - every law in .github/win107_laws.txt whose index % of == chunk is
run as `python tv/<law>.py` (untampered, read-only), bounded; <outdir>/<law>.txt holds its exit code, seconds and the
last 200 lines of its output, and <outdir>/summary.tsv one row per law. Never edits the tree.
"""
import os
import subprocess
import sys
import time

chunk, of, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
os.makedirs(out, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
laws = [l.strip() for l in open(os.path.join(here, "win107_laws.txt"), encoding="utf-8") if l.strip()]
rows = []
for i, law in enumerate(laws):
    if i % of != chunk:
        continue
    cap = 900 if law == "test_control" else 420
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, os.path.join(root, "tv", law + ".py")], cwd=os.path.join(root, "tv"),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=cap)
        rc, text = p.returncode, (p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        rc = "TIMEOUT"
        so = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        se = e.stderr.decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        text = so + "\n--- stderr ---\n" + se
    dt = round(time.time() - t0, 1)
    tail = "\n".join(text.splitlines()[-200:])
    with open(os.path.join(out, law + ".txt"), "w", encoding="utf-8") as fh:
        fh.write("law %s\nrc %s\nseconds %s\n\n%s\n" % (law, rc, dt, tail))
    last = [l for l in text.splitlines() if l.strip()]
    rows.append("%s\t%s\t%s\t%s" % (law, rc, dt, (last[-1] if last else "")[:200]))
    print("%-62s rc=%-8s %6.1fs" % (law, rc, dt), flush=True)
with open(os.path.join(out, "summary.tsv"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(rows) + "\n")
