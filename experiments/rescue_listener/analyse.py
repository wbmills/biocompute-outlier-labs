# usage: uv run --project ../rescue-listener/biocomp-spine python analyse.py a [b c]   (reads <tag>.pkl from runprobe.py)
# Prints the primary numbers per run; for the first tag, 4 raster PNGs (one per condition) and the tail check:
# does activity left by the last history pulse (600 ms) predict the probe-window count (820-1050 ms)?
# Raster unit: ms bins in which any read electrode spiked (the trial record's raster field), times from history onset.
import os, pickle, sys
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
CONDS = ("A+", "A-", "B+", "B-")
PULSES = {"A": [0, 200, 400, 600], "B": [0, 100, 500, 600]}
TAIL, PRE_PROBE = (620, 800), (700, 800)       # after the last history pulse; the 100 ms just before the probe slot


def load(tag):
    return pickle.load(open(os.path.join(HERE, f"{tag}.pkl"), "rb"))


def count(raster, w):
    return sum(w[0] <= t < w[1] for t in raster)


for tag in sys.argv[1:]:
    p = load(tag)["result"]["primary"]
    print(f"({tag}) D mean {p['mean']:+.2f}, 95% CI {p['ci'][0]} to {p['ci'][1]}, p = {p['p']:.3g}, "
          f"median {p['median']:+.1f}, D > 0 in {p['share_pos']:.0%}, {p['n']} blocks")

tag = sys.argv[1]
run = load(tag); trials, r = run["trials"], run["result"]
y0, y1 = r["y_window_ms"]; probe_w = (800 + y0, 800 + y1)
fig_paths = []
for c in CONDS:
    ts = [t for t in trials if t["cond"] == c]
    fig, ax = plt.subplots(figsize=(8, 4))
    for i, t in enumerate(ts):
        ax.vlines(t["raster"], i + 0.6, i + 1.4, lw=0.8, color="k")
    for x in PULSES[c[0]] + ([800] if c[1] == "+" else []):
        ax.axvline(x, color="tab:red" if x < 800 else "tab:blue", lw=0.8, alpha=0.7)
    if c[1] == "-": ax.axvline(800, color="tab:blue", lw=0.8, ls=":", alpha=0.7)
    ax.axvspan(*probe_w, color="tab:blue", alpha=0.08)
    ax.set(xlabel="ms from history onset", ylabel="trial", title=f"({tag}) {c}: ms bins with a read-electrode spike; "
           f"red = history pulses, blue = probe ({'omitted' if c[1] == '-' else 'delivered'}), shaded = Y window")
    ax.title.set_fontsize(8)
    path = os.path.join(HERE, f"raster-{tag}-{c.replace('+', 'plus').replace('-', 'minus')}.png")
    fig.tight_layout(); fig.savefig(path, dpi=120); plt.close(fig); fig_paths.append(path)
print("rasters:", *fig_paths)

# tail check: per condition, mean counts in the tail of the last history pulse, just before the probe, and in the Y window
print(f"\ntail check ({tag}), mean ms-bins with a spike per trial:")
print("cond   tail 620-800   pre-probe 700-800   Y window", probe_w)
rows = {}
for c in CONDS:
    ts = [t for t in trials if t["cond"] == c]
    rows[c] = [np.mean([count(t["raster"], w) for t in ts]) for w in (TAIL, PRE_PROBE, probe_w)]
    print(f"{c:4} {rows[c][0]:12.2f} {rows[c][1]:18.2f} {rows[c][2]:10.2f}   (Y from the record: "
          f"{np.mean([t['y'] for t in ts]):.2f} spikes)")
# within the probe trials: does more leftover before the probe go with a smaller (refractory) or bigger (residual
# voltage) probe response? Spearman over trials, A+ and B+ pooled and separately
from scipy.stats import spearmanr
for sel in (("A+",), ("B+",), ("A+", "B+")):
    ts = [t for t in trials if t["cond"] in sel]
    x, y = [count(t["raster"], TAIL) for t in ts], [t["y"] for t in ts]
    rho, pv = spearmanr(x, y) if np.std(x) and np.std(y) else (float("nan"), float("nan"))
    print(f"{'+'.join(sel)}: tail count vs Y, Spearman rho {rho:+.2f}, p {pv:.2g}, n {len(ts)}")
# the per-block D against the per-block difference in tails (A- tail minus B- tail)
by = {}
for t in trials: by.setdefault(t["block"], {})[t["cond"]] = t
bl = [b for b in by.values() if len(b) == 4]
d = [(b["A+"]["y"] - b["A-"]["y"]) - (b["B+"]["y"] - b["B-"]["y"]) for b in bl]
dt = [count(b["A+"]["raster"], TAIL) + count(b["A-"]["raster"], TAIL) - count(b["B+"]["raster"], TAIL)
      - count(b["B-"]["raster"], TAIL) for b in bl]
rho, pv = spearmanr(dt, d) if np.std(dt) and np.std(d) else (float("nan"), float("nan"))
print(f"per block: D vs (A tails - B tails), Spearman rho {rho:+.2f}, p {pv:.2g}, n {len(bl)}")
