# NeuroHear

> **Tonight: cl-sdk simulator only, no living neurons.** No CL1 hardware is used. Every result is
> SIMULATED and carries its provenance badge.

Adaptive neural I/O for biological computing. A digital YES/NO message is compiled into
electrode pulses, the neural response is recorded, and a leakage-safe decoder tries to recover
the message from the post-stimulus response alone. An optimiser compares pre-registered
encodings on validation trials, locks the best one, and tests it against the baseline on sealed
held-out trials, with negative controls.

**This build runs against a declared mathematical tissue model. It contains no living-neuron data.**
Every number in the UI and every exported file carries its provenance.

## Run it

```bash
./scripts/run_local.sh            # creates .venv on first run, serves http://localhost:8000
./scripts/smoke_test.sh           # full protocol via the API + export, no code edits (~30 s)
python -m pytest -q               # 51 tests, ~30 s (1 skips when cl-sdk is installed)
```

Needs Python 3.12+ (cl-sdk requirement; `run_local.sh` refuses older) and `requirements.txt`
(numpy, scipy, scikit-learn, starlette, uvicorn) plus `cl-sdk`. The simulated sources alone also run on 3.11.
The dashboard is plain HTML/JS served by the backend: no npm, no build step, no internet needed.
Install dependencies **before** the event.

## Demo flow (dashboard)

1. Say "yes"/"no" (browser speech recognition, labelled as such) or press **Yes / No**, then **Send to neurons**.
   The pulse pattern, raster (with artifact blanking and decoder window) and decoded label appear.
2. **Record spontaneous activity** → active channels, baseline rate (no stimulation).
3. **Run baseline** → 24 calibration trials of the baseline rate code.
4. **Optimise** → 72 trials of 3 order-code candidates, interleaved; decoders fit on train, chosen on validation, then frozen.
5. **Run locked test** → 40 sealed trials (baseline vs chosen, interleaved) + controls. Report + evidence slide written to `runs/<run_id>/`.
6. **Export** → zip (report.json, trials.csv, trials.jsonl, audit.jsonl, evidence.md) + raster PNG.

Reference result (seed 123, `artifacts/sample_evidence.md`): baseline 11/20, chosen `B_order_ipi60` 20/20,
permutation p = 0.005, no-response (artifact-only) control 24/40 (p = 0.13 vs chance, not significant),
unmasked-artifact diagnostic 100%.
The model's preference for 60 ms spacing exists **by construction** (short-term depression, saturation, inhibition).

## Tonight's three sources

```bash
NEUROHEAR_SOURCE=cl_sdk_sim   ./scripts/run_local.sh   # main demo: tissue model driven through the real cl API
NEUROHEAR_SOURCE=sdk_random   ./scripts/run_local.sh   # live negative control: spikes ignore stimulation
NEUROHEAR_SOURCE=reactive_sim ./scripts/run_local.sh   # fallback without cl-sdk; reproduces the reference result
```

Swap `run_local.sh` for `smoke_test.sh` to run the full protocol headless.

## Spoken yes/no (raw audio, no speech recognition)

The sound itself becomes pulses (`backend/encoding/audio.py`): 8 frequency bands x 5 time slices, the 2
strongest bands per slice, one electrode per band on row 8-15. Every recording gets 10 pulses at the same
times and charge. `backend/experiment/audio_protocol.py` holds out whole speakers and reports the cells'
response next to a no-cells readout of the pulse pattern, permuted labels and (on `reactive_sim`) an
artifact-only control.

```bash
./scripts/make_tts_dataset.sh                       # 84 synthetic-speech files (21 macOS voices x 2 rates)
./scripts/record_voice.sh <name> 10                 # human takes -> data/audio/human/ (git-ignored)
.venv/bin/python -m backend.experiment.audio_protocol --source cl_sdk_sim
```

Seed 123, 7 of 21 voices held out (28 recordings): `cl_sdk_sim` 23/28, `reactive_sim` 22/28, `sdk_random` 13/28
(chance); the pulse pattern alone scores 26/28. The intervals overlap and the difference was not tested,
so this is no evidence the simulated cells add information, not proof that they add none.
The dashboard's **Speak into the culture** button sends 1.5 s of microphone audio through the same path
(`POST /audio-trial`) and decodes it with a readout trained on the whole dataset. It has no true label, so it
is never scored. Expect roughly 1 in 5 live decodes wrong.

## Planted-learning positive control (failed)

`TissueConfig(plasticity=True)` turns on a pair-based STDP rule on the fast gains (off by default; output is
then bitwise identical to before). `scripts/learning_demo.py` pairs the order code with a hint pulse on a Y or
N output group: contingent on the word, at random (sham), or with plasticity off. Pre-registered rule:
contingent beats both by >= 15 points. Result after one tuning pass: 52% vs 48% and 49%, so **not passed**.
Outputs go to `runs/learning_demo/`. This is learning we programmed, labelled as such, not biology.

## Data sources

| Source | What it is | Badge |
|---|---|---|
| `reactive_sim` (default) | Seeded, non-learning tissue model that responds only to delivered pulse events | SIMULATED MODEL |
| `sdk_random` | Stimulus-independent spikes: our tissue model with stimulus gain and artifact set to 0 (negative control; not cl-sdk's built-in random source) | SIMULATED (RANDOM…) |
| `replay` | Replays a recorded run; refuses any schedule not actually delivered | REPLAY OF … (original provenance) |
| `cl_sdk_sim` | `cl` API + cl-sdk simulator with the reactive model registered as a custom data source | SIMULATED MODEL VIA CL-SDK |
| `live_cl1` | `cl` API on hardware. Read-only unless all three interlocks pass | LIVE CL1 |

Live interlocks (fail closed): `LIVE_STIM_ENABLED=true`, a complete `OPERATOR_LIMITS` JSON from the lab operator
(template: `operator_limits.example.json`, which is deliberately rejected as-is), and `POST /operator/approve`.
Every stim command, delivered or rejected, goes to `audit.jsonl`. **Stop** aborts the run and calls `interrupt()`.

## Integrity guarantees (tested)

- Backends receive pulses only (`run_trial(pulses)`); labels are attached after acquisition.
- Same seed + same pulses → bitwise-identical response; label is not an input anywhere.
- `gain=0` removes stimulus dependence; random source decodes at chance over seeds.
- Artifact: a class-correlated artifact decodes at >90% without the mask and at chance with it.
- Splits pre-assigned from the seed; whole trials disjoint; scaler + decoder fit on train only;
  encoder chosen on validation only; decoders fingerprinted and frozen before any test trial is acquired.
- Replay cannot fabricate counterfactual responses.
- Out-of-order steps are refused without changing state.

## Verified tonight (3 Nov 2026, cl-sdk simulator only)

- Python 3.12.14, **cl-sdk 1.0.0** (`.venv`). API calls checked against the installed SDK source.
- `./scripts/smoke_test.sh`, seed 123, held-out (sealed test) results:

| Source | Baseline `A_rate` | Chosen | Notes |
|---|---|---|---|
| `cl_sdk_sim` | 12/20 | `B_order_ipi60` 20/20 | permutation p = 0.005; `scheduled_lateness_ms` 0.0 and `stim_alignment_error_ms` 0.0 on all 136 trials, stims observed in every trial; no-response control not run on this source |
| `sdk_random` | 10/20 (bal. acc 0.50) | baseline kept | verdict "No demonstrated gain" |
| `reactive_sim` | 11/20 | `B_order_ipi60` 20/20 | identical to `artifacts/sample_evidence.md` |

- On the simulator, `cl1_adapter.py` defaults `CL_SDK_VISUALISATION=0` (its visualiser otherwise takes port 8000)
  and `CL_SDK_ACCELERATED_TIME=1` (the wall-clock producer runs the reactive source slower than real time).
  Set either explicitly to override.
- Numbers are after the grounded/reference-channel fix (below). Before it: `sdk_random` 11/20, `reactive_sim` 19/20,
  `cl_sdk_sim` unchanged, so the result did not depend on those channels.
- `cl_sdk_sim` numbers are for a fresh server with nothing clicked first. Its noise follows the cl-sdk clock, so
  earlier trials or runs on the same server change later results (seen: baseline 15/20 and 17/20, chosen 19–20/20).
- `cl_sdk_sim` numbers differ from `reactive_sim` because the same model's noise is drawn through the cl-sdk data
  source path. Both are SIMULATED.

## Grounded and reference channels

On a CL1, channels 0, 7, 56 and 63 are unused and 4 is the reference (`SILENT_CHANNELS` in `backend/schema.py`).
The simulators record nothing there (the simulated network beneath them still runs), and the decoder's features
zero them for every source, so no result can come from a channel real hardware does not record.
`tests/test_silent_channels.py` covers both and fails on the code before the fix.

## Not verified

- **Hardware**: never tested. Lead-time scheduling, `read(..., analysis=True)` on past windows and µV scaling
  must be checked with the operator. Alignment error is logged per trial (`stim_alignment_error_ms`).
- **PSD feature path** is computed and stored for simulated raw voltage but the decoder uses spike features (v1).

## Deviations from SPEC.md

- Dashboard is vanilla JS (no React/Vite) and the server is Starlette (FastAPI's base) — no build step, fewer installs on event Wi-Fi.
- Events use Server-Sent Events at `/events` instead of a WebSocket; payloads match §13.
- `encoding/rate.py` + `temporal.py` are merged into `encoding/encoders.py`.

## Layout

```
backend/app.py                    API + dashboard server
backend/schema.py                 StimPulse, Trial, Acquisition, NeuralBackend, provenance
backend/encoding/                 encoders (rate + order codes, candidate grid), safety gate
backend/acquisition/              simulator, replay, cl-sdk / CL1 adapters
backend/simulations/              tissue model + cl-sdk data source
backend/experiment/               features, decoder, metrics, controls, scheduler, persistence
backend/static/                   dashboard
tests/                            51 tests (spec §14)
artifacts/                        sample report, evidence slide, captioned simulated demo video
PITCH.md                          90-second script, slide outline, valid / invalid claims
```

Event-rule note: this code was prepared before the event. Ask the organisers whether pre-built code is
allowed and say plainly that it was.
