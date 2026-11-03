# Rescue Listener: does the same input get a different answer depending on its history?

Biocomputing Hack, Halkin, 3 November 2026. Solo team (atiladeokegab).
Full product code (live screen, 3D scene, data, tests): https://github.com/atiladeokegab/rescue-listener

Everything in this folder ran on **this repository's simulator** (revision `a8e9988`, the
`organoid_simulator` LIF data source through `cl-sdk 1.0.0`). It is a simulated spiking neural
network, not living tissue. No result here is about cells.

## 1. The idea

When a building collapses, trapped people may tap for help. Rescue Listener is a proposed rescue
workflow: drones drop microphones onto rubble, land, stop their rotors, and listen for a
deliberate reply (a rhythm) among background noise. The 3D scene in the product repo shows that
workflow; it is a concept, not a validated rescue system.

A listener that tells a deliberate rhythm from noise needs a system whose response to a sound
depends on what came before it. So the question we could test honestly tonight is narrow:

> **Does an identical stimulus produce a different response depending on the rhythm before it?**

That property is *history dependence*. It is not learning, and it is not memory proved.

## 2. Setup

| Item | Value |
|---|---|
| Simulator | `wbmills/biocompute-outlier-labs` at `a8e9988`, Python 3.13 |
| Data source | `organoid_simulator.lif_data_source:make_lif_source`: 64 LIF neurons, tau 20 ms, threshold −50 mV, 2 ms refractory, small-world coupling |
| SDK | `cl-sdk 1.0.0`, accelerated time, visualisation off |
| Coupling | `coupling_gain_mV` 4.0 (connected network) and 0.0 (control: no network) |
| Stimulus | input electrode 27, biphasic, 160 µs per phase, 2.0 µA |
| Read electrodes | 24 electrodes chosen before the run by a scan (listed in `results/*/frozen.json`) |
| Spike detection | the SDK's own detector, unchanged by our code |

The acquisition code talks only to the cl-sdk interface, so the same experiment runs unchanged on
a CL1. Tonight's numbers are simulator numbers.

Environment used:

```bash
CL_SDK_DATA_SOURCE=organoid_simulator.lif_data_source:make_lif_source
CL_SDK_DATA_SOURCE_CONFIG='{"coupling_gain_mV": 4.0}'   # 0.0 for the control
CL_SDK_ACCELERATED_TIME=1
CL_SDK_VISUALISATION=0
```

## 3. The pre-registered probe

The design was fixed before any data was taken (`probe_design.json`; each run freezes its full
config with a SHA-256 hash and timestamp in `frozen.json` before the first trial).

- **Two histories with the same number of pulses**, which start and end together and share
  the same gap before the probe:
  - A: pulses at 0, 200, 400, 600 ms (even rhythm)
  - B: pulses at 0, 100, 500, 600 ms (uneven rhythm)
- **A probe pulse at 800 ms**, identical in both.
- **Omission trials:** each block also plays both histories with the probe left out, so
  leftover activity from the history alone can be subtracted.
- One block = A+, A−, B+, B− in random order. 30 blocks (20 in the short version).
- **Response Y:** spikes pooled over the read electrodes 20–250 ms after the probe slot.
- **Primary statistic:**

  **D = (A+ − A−) − (B+ − B−)**

  If the network's answer to the probe does not depend on the rhythm before it, D is centred on 0.
- **Test:** two-sided sign-flip test over blocks (20,000 flips) with a 95% CI. Decision rule,
  set in advance: history effect only if p < 0.05. The p-value assumes block differences are
  sign-symmetric under the null; it is a Monte Carlo estimate, not exact.
- **Pre-declared checks:** trials with a burst in the 1 s before onset are flagged; a
  sensitivity analysis drops them; sub-windows 20–60 ms and 60–250 ms are reported
  separately; drift (first half against second half); the minimum detectable effect at 80% power.

## 4. Results

### Connected network (coupling 4.0 mV), two runs of 20 blocks

**Run 1, through the live screen in real time (seed unset):** D = +2.8 spikes, 95% CI −2.9 to
+8.6, sign-flip p = 0.34 (median +1.5). Raw trial file not attached.

**Run 2, accelerated time, seed 42** (full output, frozen config and rasters in
`results/coupled-4mV/`):

| Measure | Value |
|---|---|
| Mean Y: A+, A−, B+, B− | 26.75, 27.10, 26.45, 27.05 spikes |
| **Primary D** | **+0.25, 95% CI −2.90 to +3.44, p = 0.90**; D > 0 in 45% of blocks |
| Minimum detectable effect (80% power) | 4.6 spikes (sd of D 6.9) |
| Baseline-subtracted (sensitivity) | +0.35, 95% CI −5.80 to +6.60, p = 0.92 |
| Leftover alone, Y[A−] − Y[B−] | +0.05, p = 1.0 |
| D in 20–60 ms / 60–250 ms | −0.65 (p = 0.55) / +0.90 (p = 0.57) |
| Drift | first half −0.10, second half +0.60 |
| Tail check: activity after the last history pulse vs Y | Spearman rho −0.21, p = 0.19 (A+ and B+ pooled) |
| Decoder (secondary) | 6/20 = 30%, 95% CI 15–52% |

**Result: no history effect measured in the connected network either.** Any history effect larger
than about 3.4 spikes either way is ruled out at these settings.

### Control: no coupling (0.0 mV), 30 blocks

Full output in `results/control-coupling-0/summary.txt`; rasters for each condition beside it.

| Measure | Value |
|---|---|
| Mean Y: A+, A−, B+, B− | 19.17, 19.87, 18.37, 20.40 spikes |
| **Primary D** | **+1.33, 95% CI −1.82 to +4.47, p = 0.40**; D > 0 in 60% of blocks |
| Minimum detectable effect (80% power) | 4.5 spikes (sd of D 8.4) |
| Without pre-onset bursts | identical (0 trials flagged) |
| Baseline-subtracted (sensitivity) | +4.07, 95% CI +0.20 to +7.90, p = 0.041 |
| Leftover alone, Y[A−] − Y[B−] | −0.53, p = 0.65 |
| D in 20–60 ms / 60–250 ms | +0.80 (p = 0.26) / +0.53 (p = 0.68) |
| Drift | first half +3.13, second half −0.47 |
| Decoder (secondary) | 17/30 = 57%, 95% CI 39–73%, p = 0.29 |

**Result: no history effect measured.** That is what a control with no network should show.

One sensitivity analysis (baseline-subtracted) crosses p < 0.05 in the *control*. We report it
because it was pre-declared, but we do not read it as an effect: it is one of several secondary
analyses, the primary is null, and it appears where no network exists. It is a warning that this
statistic can move on ordinary single-neuron dynamics (refractoriness, residual membrane voltage)
alone.

## 5. What this does and does not show

- It shows a pre-registered, controlled protocol for history dependence that runs end to end
  on the organisers' simulator through the standard SDK, with its config frozen and hashed first.
- Tonight, on this simulator and these settings, **neither the connected network nor the control
  showed a history effect we can tell apart from chance.** We report the null plainly.
- It does not show learning, memory, or survivor detection.
- Deterministic reruns of the same seed are not independent evidence; each run's seed is
  recorded.

## 6. Reproduce

From this repository's root, with the product code checked out beside it
(`git clone https://github.com/atiladeokegab/rescue-listener ../rescue-listener`):

```bash
uv sync
CL_SDK_DATA_SOURCE=organoid_simulator.lif_data_source:make_lif_source \
CL_SDK_DATA_SOURCE_CONFIG='{"coupling_gain_mV": 0.0}' \
CL_SDK_ACCELERATED_TIME=1 CL_SDK_VISUALISATION=0 \
PYTHONPATH=../rescue-listener/biocomp-spine \
uv run --with scikit-learn python experiments/rescue_listener/runprobe.py control
```

`runprobe.py` writes `control.pkl` (every trial, rasters included) and prints the summary.
`analyse.py control` prints the primary numbers, draws one raster per condition and runs the
tail check (does activity left by the last history pulse predict the probe-window count?).

The live screen (`live.py --rhythm` in the product repo) runs the same protocol in a browser,
labelled "Simulator running live" only while it is computing; anything prerecorded is labelled
"Replay".

## 7. Next step

Run the unchanged protocol on a CL1, keep the coupling-zero analogue (no-stimulus and shuffled
controls), raise the block count until the minimum detectable effect is below 2 spikes, and
report a null as plainly as a positive.
