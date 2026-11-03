# NeuroHear: where we are (3 Nov 2026, evening)

**Tonight is simulator only. There are no living neurons and no CL1 hardware.** Every result below is
SIMULATED and carries that badge in the app and in every exported file.

## The one-line version

We send a spoken or button-pressed "yes" or "no" into (simulated) brain cells as electrical pulses, record
how the cells react, and check whether a simple readout can tell yes from no using the reaction alone.
It works. The pipeline runs on the real Cortical Labs software (cl-sdk), and our controls catch the usual
ways such results get faked.

## Are the neurons learning?

**No.**

1. **There are no real neurons tonight.**
2. **The simulator we use does not learn, on purpose.** Its connections are fixed numbers set when it is
   created. That is the standard *reservoir computing* setup: the cells are left alone, recent input
   lingers in their activity ("fading memory"), and only a simple linear readout on the output is trained.
   NeuroHear has always worked this way.
3. **We also tried a "planted learning" test.** We added an optional learning rule to the simulator, off by
   default, to check that our analysis would spot learning if it were there. That is learning we
   programmed, not biology. Even so, **the test failed**: the analysis did not detect the planted learning
   (details below). So we cannot yet claim the protocol would detect learning in real cells.

## How it works

| Part | What it does |
|---|---|
| **Encoder** | Turns yes/no into pulses on electrodes 8 and 9 (pair A) and 18 and 19 (pair B). Every pulse is 1 µA and 160 µs, and yes and no always get the same number of pulses and the same charge. The best code found: yes = A A B B, no = B B A A, 60 ms apart. |
| **Audio encoder (new)** | Turns the *sound* of a recording into pulses: 8 frequency bands × 5 time slices, the 2 strongest bands per slice. Every recording gets 10 pulses at the same times; only *which* electrodes fire carries information. No speech recognition is involved. |
| **"Neurons" (simulated)** | A fixed model: each pulse makes nearby channels fire, with fatigue, saturation, damping, background noise, slow drift and fake artifact blips. It never sees the word. |
| **Decoder / readout** | Skips the stimulation (blanks 5 ms after each pulse, starts reading 10 ms after the last one), counts spikes per channel in 4 slices of 100 ms, and makes a weighted yes/no vote (logistic regression). It is trained on some trials and tested on trials or speakers it has never seen. |

## What we checked and fixed tonight

- **Environment:** Python 3.12.14 and cl-sdk 1.0.0, in `neurohear/.venv`.
- **cl-sdk compatibility:** every call we make matches the installed SDK. Two fixes were needed:
  - cl-sdk's own viewer was taking port 8000 before the dashboard could, so it is now off by default.
  - Its real-time clock ran our model too slowly, so we now use cl-sdk's documented accelerated time.
  - Stimulation timing is exactly 0 ms off on every trial.
- **A cheat we found and removed:** on a real CL1, channels 0, 7, 56 and 63 are unused and 4 is the
  reference. Our simulator let channels 0 and 4 react to pair A only, which gave the decoder a clue a real
  chip never would. These five channels are now blank in the simulator and ignored by the decoder, and
  tests guard this. Scores stayed the same or went up, so the result never depended on the cheat.
- **Checked against the organisers' repo** (`wbmills/biocompute-outlier-labs`):
  - The data format, stimulation limits and channels match.
  - Their simulator has a learning rule, but it needs a reward signal that cannot get through cl-sdk.

## Results (seed 123)

### Main demo: button yes/no, 20 held-out trials per code

| Source | Baseline code | Best code | Notes |
|---|---|---|---|
| `cl_sdk_sim` (main demo) | 12/20 | 20/20 | Shuffled labels p = 0.005. Numbers shift if anything was clicked earlier on the same server, so read them off the cards. |
| `sdk_random` (cells ignore pulses) | 10/20 | none: baseline kept | The negative control. Chance, as it should be. |
| `reactive_sim` (fallback) | 11/20 | 20/20 | Artifact-only control 24/40 (p = 0.13, not significant); without blanking, 100%. |

### Spoken yes/no: 84 synthetic-speech recordings, 7 of 21 voices held out (28 test recordings)

| Source | Cells' response | Pulse pattern alone (no cells) | Notes |
|---|---|---|---|
| `cl_sdk_sim` | 23/28 (p = 0.02) | 26/28 | |
| `reactive_sim` | 22/28 (p = 0.015) | 26/28 | Artifact only: 13/28, chance |
| `sdk_random` | 13/28 (p = 0.70), chance | 26/28 | |

**What this means:** the sound's pattern survives the trip through the simulated cells, well above chance.
Reading the pulses directly scored higher (26/28 vs 22–23/28), but the 95% intervals overlap (about
59–94% vs 76–99%) and the difference was not tested. So the honest wording is: **we found no evidence
that the simulated cells add information**, not that they add nothing. The
recordings are macOS text-to-speech voices, not human speech; no human voices have been recorded yet.

### Planted-learning positive control (5 seeds, 100 probe trials per point)

| Condition | First block | Last block |
|---|---|---|
| Hint follows the word ("contingent") | 48% | 52% |
| Hint at random ("sham") | 46% | 48% |
| Learning rule off | 49% | 49% |

The pre-registered rule was that contingent beats both controls by at least 15 points. It managed 3, so
**it did not pass**. One tuning pass was allowed and used. The cause: the two output groups sit next to
each other and one input already drove an output channel directly, so the rule strengthened connections to
both groups instead of the right one. Moving the groups apart is a design change and has not been done.

## What we can and cannot say

**Can say:**
- The full pipeline runs on the real Cortical Labs software, with exact stimulation timing.
- Our controls catch the stimulation-artifact trap and random data.
- The protocol is ready to run on a CL1.

**Cannot say:**
- That cells hear, understand or learn anything.
- That anything here is evidence about real neurons. The simulator prefers our best code because we
  built it that way.
- That the planted-learning test worked: it failed.
- That the 60 ms code is generally best. Results are from one seed (123); a 10-seed sweep (Yong's notes,
  not re-run here) picked a different winning code in 5 of 10 seeds. Re-running seed 123 is a
  reproducibility check, not an independent replication.

Tonight's run summaries (evidence and report for each run, plus the planted-learning figure) are in
`results/2026-11-03/`.

## Commands (from `neurohear/`)

```bash
NEUROHEAR_SOURCE=cl_sdk_sim ./scripts/run_local.sh             # dashboard: http://localhost:8000
NEUROHEAR_SOURCE=cl_sdk_sim ./scripts/smoke_test.sh            # full protocol headless (~30 s)
./scripts/make_tts_dataset.sh                                  # build the synthetic-speech set
./scripts/record_voice.sh <your_name> 10                       # add your own yes/no recordings
.venv/bin/python -m backend.experiment.audio_protocol --source cl_sdk_sim   # spoken yes/no results
.venv/bin/python scripts/learning_demo.py                      # planted-learning control + figure
.venv/bin/python -m pytest -q                                  # 51 tests
```

## Not done yet

- **"Speak into the culture" button:** live microphone audio into the cells. It works through the API, but
  nobody has clicked it in a real browser yet. Expect about 1 in 5 live decodes to be wrong, and the
  confidence figures are overstated.
- **Human voice recordings:** none yet, so the readout is trained only on synthetic voices.
- **The artifact-only control on `cl_sdk_sim`.**
- **Frequency-band (PSD) decoding:** the approach your notes found better on real cells. It is computed
  but not used.
- **The backup video:** `artifacts/preflight_demo_SIMULATED.mp4` predates tonight's changes and may show
  old numbers.
