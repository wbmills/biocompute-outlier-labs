# usage (from the sim repo root): uv run python runprobe.py <tag>; writes <tag>.pkl (the full result) and prints probe.fmt
# Each run gets its own frozen-<tag>.json, so parallel runs never share one.
import os, pickle, sys
import bci, probe
tag = sys.argv[1]; out = os.path.dirname(os.path.abspath(__file__))
recs = []   # every trial record, rasters included (run() returns only the analysis)
with bci.cl.open() as neurons:
    r = probe.run(neurons, 0, probe.D["blocks"], path=os.path.join(out, f"frozen-{tag}.json"), on_trial=recs.append)
pickle.dump(dict(result=r, trials=recs), open(os.path.join(out, f"{tag}.pkl"), "wb"))
print(f"source: {bci.source()}"); print(probe.fmt(r))
