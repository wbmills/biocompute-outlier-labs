# NEUROHEAR — AGENT-READY BUILD SPECIFICATION
**Version:** 1.0 | **Prepared:** 2 November 2026 | **Event:** Outlier Labs × Project A Biocomputing Hack, London, 3 November 2026
**Working name:** NeuroHear | **Technical subtitle:** Adaptive Neural I/O / Biological Encoding Optimiser
**Scope:** pre-event preparation + a two-hour on-site experiment. **This is a build specification, not an assertion that live CL1 access is provided.**

---

## 0. EXECUTIVE BRIEF — READ FIRST

### The one-sentence product
NeuroHear is a programmable communication layer that converts a simple spoken command into an electrode stimulation pattern, records the resulting neuronal response, and systematically searches for encoding parameters that make the response easier to distinguish at a controlled stimulation budget.

### The scientific question
**Can feedback from a living neural network tell us which electrical code transmits a binary message more reliably to that particular biological culture?**

This is not speech understanding, auditory perception, biological speech recognition, proof of neuronal learning, cochlear-implant validation, or evidence that biological computing beats silicon. A digital speech recogniser (or explicit button) selects the command *before* electrode encoding. The biology is the stimulated, measured channel; the decoder tries to reconstruct which command was transmitted from neural readout alone.

### What the demonstrator must show
1. Judge speaks **YES** or **NO** (fallback: clicks a clearly disclosed YES/NO button).
2. Browser displays sound waveform or microphone level, recognised label, and the electrical pulse pattern translated from that label.
3. A CL1-compatible backend dispatches stimulation (in live mode only with operator approval) or routes it through a clearly labelled reactive simulator.
4. A neural-response view shows time-aligned spikes or recorded voltages, with stimulation artifact intervals shaded/excluded.
5. A decoder predicts which message was sent, with a confidence/readout score and a clearly visible provenance badge: **SIMULATED**, **RECORDED BIOLOGICAL**, or **LIVE CL1**.
6. **The wow beat:** the judge clicks **OPTIMISE**, sees candidate encodings tested against the culture/model, watches the relative response-separability scores update, and then sends a new message using the best candidate. The key result is the validated difference in post-stimulation neural-response separability, not a preordained 100% classification animation.

### Success hierarchy
- **Minimum (reliable):** working microphone-to-encoder-to-CL-SDK-compatible model-to-decoder-to-dashboard flow; fixed, honest synthetic metrics; repeatable automated tests.
- **Good:** functioning candidate search with held-out validation in the stimulation-reactive simulator; artifact and label-shuffle controls; downloadable run logs.
- **Excellent:** real CL1 integration, recorded stimulus-locked responses, a randomized baseline/optimised comparison, and non-artifactual classification above negative controls.
- **Scientific stretch:** biological response separability improves at matched charge/pulse budget on independent held-out trials. Not guaranteed and must not be represented as guaranteed.

### Top three non-negotiables
- Never imply simulated activity came from living neurons.
- Never claim neurons hear, recognise spoken words, or learned if only decoder/encoder parameters improved.
- Never use the class label directly or indirectly to generate a simulation's neural response after stimulation. The simulated response depends on delivered pulse events and a seeded tissue model, not on ground-truth labels.

---

## 1. EVENT ASSUMPTIONS AND RULES

Official event: https://luma.com/2khmpnqp
- Tuesday 3 November 2026, 18:30–22:00 London time.
- 19:00 tutorial by Callosum and Frontier Computing; 19:30–21:30 solo build; 21:30–22:00 pitches.
- Prize: one day's access to a Cortical Labs CL1.
- Event wording says *build something great by yourself*. It does **not** explicitly settle permissibility of prebuilt code, AI coding agents, cloud accounts, prerecorded videos, or on-site live neuronal hardware. **Ask organiser.** Distinguish preparatory code from on-site original work. Do not claim pre-event work was created during the hackathon, and honour any prebuild restrictions.

At arrival ask:
1. Is local CL-SDK simulator the intended execution environment, or is any live CL1/neural recording access available during the build? If live, who approves stims?
2. Are reusable codebases, libraries, prepared UI assets, and AI coding agents allowed? Are there restrictions on pre-event work?
3. Which electrodes/channels, pulse intensity limits, trial frequency and stimulation protocols are allowed?
4. Do organisers supply recorded, **stimulus-labelled** neural response datasets, or example CL1 applications?
5. Is internet/Wi-Fi reliable? Can we run local Python services and a browser microphone? Can pitches show a screen?

If prebuilt work is disallowed: only use what is explicitly permitted at the event. Do not disguise preparatory implementation as on-site work.

---

## 2. RESEARCH — EVIDENCE TO ENGINEERING DECISIONS

**A. Smirnova & Hartung (2022), Neuron, 10.1016/j.neuron.2022.11.010.**
A short commentary on Kagan et al.'s DishBrain Pong experiment (original: https://pmc.ncbi.nlm.nih.gov/articles/PMC9747182/). The original experiment demonstrates the value of a structured electrical input, neural readout, a simple embodied environment, and feedback. **Our decision:** make a visibly bidirectional system, but do not imply a spoken command is understood or that a binary classifier proves learning.

**B. Robbins et al. (2026), Cell Reports, 10.1016/j.celrep.2026.116984.**
The experiment used spontaneous neural characterisation, stimulus-response/causal connectivity mapping, and adaptive training in a CartPole task. Results span 19 organoids, 41 experiments and >125 recording hours. Most organoids benefited from adaptive vs random/no training, but performance gains were not sustained after a 45-minute rest period. **Our decision:** use a 2-stage protocol: small preflight electrode/site characterisation followed by optimisation on measured evoked responses; compare random/fixed vs adaptive codes; do not promise biological learning in a two-hour hack.

**C. Loeffler et al. (2026), bioRxiv preprint, 10.64898/2026.08.10.743829.**
CL1 reservoir computing with human iPSC-derived neuronal cultures on spatiotemporal MNIST stimulation. Crucial observations: decoding methodology changes accuracy; modular cortical network structure matters; input stimulation artifacts can inflate results (including non-cell saline recordings); whole-trial cross-validation is more trustworthy than splitting time bins across train/test; band-power features on raw poststim signals can outperform simple time-bin spike-count features. A 400-ms response period starting 10 ms after final stim was used for the frequency-domain analysis. **Our decision:** implement a post-stim artifact-free feature window, trial-level train/validation/test split, no-cell/synthetic/permuted controls where available, and a PSD feature path as optional/primary if raw voltages are available. Do not imply their preprint is established peer-reviewed clinical evidence.

**Company alignment:**
- CL1: programmable bidirectional electrical stimulation/readout, living neuronal cultures, software-defined environment: https://corticallabs.com/cl1
- Callosum: systems-level integration of heterogeneous computing and intelligence; our value is the translation/abstraction layer rather than another model: https://www.callosum.com/
- Frontier Computing: scalable biological computing and learning; our approach measures how information passes into a living substrate: https://frontier.site/

**Citations in presentation:** include the three DOIs; avoid claiming clinical performance improvements or comparative energy efficiency.

---

## 3. PRODUCT POSITIONING AND WOW DEMO

### Name and hook
**NeuroHear: The language compiler for living neurons.**
Tagline: **Speak into a microphone. Watch a biological neural network respond. Let software discover the best electrical language.**

### 70–90 second ideal demo sequence
**0–10 s — Attention.** Ask a judge to say YES or NO. Display microphone waveform and digitally recognised command. Say explicitly, "The microphone is conventional software; the interesting step starts here."
**10–20 s — Translation.** Show the class mapped to a patterned series of electrode pulses, visible on a channel × time matrix.
**20–35 s — Biological response.** Run stimulation and show multichannel neural spikes/readout. Label the source at all times. Shade artifact windows. Live only if hardware actually used.
**35–50 s — Decoder.** Hide labels from the decoder; display prediction from post-stim neural features. The on-screen command is verified against the held-out label after prediction.
**50–70 s — Optimisation.** Click OPTIMISE to evaluate candidate patterns and show their measured separability vs pulse cost. Choose the winner on training/validation data, lock it and run a fresh test.
**70–85 s — Reveal.** Show candidate A vs candidate B and the negative control. Do not fake success; if live results are unconvincing say "this run establishes the instrument and test protocol, not a positive biological finding" and show reproducible simulator demonstration separately.
**85–90 s — Market.** "A programmable, experimentally optimised I/O protocol is a prerequisite for scaling biological computing. A future clinical application is neural prosthesis coding."

### The single visual to get right
Three synchronised panels:
1. **HUMAN INPUT:** mic bar + YES/NO token.
2. **ELECTRICAL ENCODING:** channel-by-time pulse pattern in bright accent colour.
3. **NEURAL OUTPUT:** live/replayed/simulated raster (or voltage trace) with artifact mask.
Below: two encoder scorecards (**Baseline** / **Optimised**) and a compact 0–100% held-out readout metric. Always disclose N and source (e.g., `SIMULATED MODEL · n=20 held-out trials`).

### Pitfall
If the digital recogniser maps YES to a known pulse sequence, the system has not learned speech. Its task is **recovering a deliberately encoded message from recorded neural activity**, not acoustic understanding. An electrically coded word can also be directly decoded from the input pulse train, so this is **not evidence that neural hardware outperforms silicon**. It is evidence of a programmable neuronal I/O experiment and, if supported by live data and proper controls, an optimisable neural-response channel.

---

## 4. EXACT SCOPE, PRIORITIES, AND NON-GOALS

### Priority 0 (must ship before arrival if permitted)
- One-command local startup; no cloud dependency.
- Browser UI with microphone and explicit buttons.
- Digital keyword selection / operator confirmation; no open-ended ASR requirement.
- Two electrical encoders with identical limits and stimulus budget.
- Fake hardware **only** as a correctly labelled reactive simulator adapter, with reproducible random seed.
- Unified trial log: timestamped stim, response, feature extraction, model decision, labels, data source.
- Controlled experiment: fixed vs candidate strategies, shuffled trial order, train/validation/test split.
- Two features: simple poststim spike-count features + optional PSD on raw signal.
- Baselines: label permutation, no-stim/synthetic random, artifact mask.
- Save/replay session; robust offline demonstration.

### Priority 1 (on-site)
- Confirm regulations and runtime, bind to CL-SDK/recording adapter.
- Live trial collection if available; otherwise build an actual event-specific experiment and report using simulation clearly.
- Baseline vs alternative encoder assessment on disjoint test trials.
- Debug and validate source provenance + acquisition timing.
- Record pitch demo or run it live; freeze reproducible results.

### Stretch (only after P0/P1 pass)
- Automated parameter search with Bayesian optimisation / multiarmed bandit (grid search is acceptable and more reliable).
- 3+ input categories (avoid unless binary works robustly).
- Multi-electrode topography heatmap and causal response map.
- Browser speech recognition as optional, with noisy-room fallback.
- Alternative experiment: perturbations / trial-state adaptation if more lab access is granted.

### Explicit non-goals
- No neural speech comprehension, training speech perception, TTS output from neurons, ASR from spiking activity, long-term tissue learning, cochlear implant validation, clinical benefit, or universal encoding discovery.
- No unapproved stimulation. No promises that any protocol reliably changes neuronal activity on a fresh chip.
- No production-grade web deployment or external account integration.

---

## 5. USER EXPERIENCE AND FRONTEND REQUIREMENTS

### Stack
TypeScript + React + Vite, Tailwind optional, Plotly or lightweight Canvas/SVG raster chart, WebSocket for live events, browser MediaDevices microphone (`getUserMedia`) in localhost/secure context. Avoid heavy animation libraries. Audio capture should never block the neural acquisition loop. Python 3.11+ FastAPI backend, NumPy, SciPy, scikit-learn, pytest; `cl-sdk` optional at startup and pinned/tested separately.

### Page layout (laptop/projector 16:9)
**Top:** NeuroHear logo; source flag (`SIMULATED`, `RECORDED NEURAL`, `LIVE CL1`); system status, seed, experiment ID, acquisition state.
**Left 35%:** microphone button; "Say YES or NO"; displayed digital recognised command; fallback yes/no buttons; wave level; pulse matrix across channels/time.
**Centre 40%:** raster / neural response; red shaded artifact windows; actual timestamp and trial #; visual latency.
**Right 25%:** decoded label and score; baseline/optimised cards; live leaderboard of candidate encoders; negative-control comparison.
**Bottom:** START CALIBRATION, RUN BASELINE, OPTIMISE, RUN LOCKED TEST, RESET, EXPORT; info line with `n_train`, `n_val`, `n_test`, `active channels`, `last stim`, `errors`.

### Interactions
- `Speak`: capture short audio; local recognition in browser if supported, otherwise confirm YES or NO manually. Explicitly label browser-recognised words as digital recognition. No silent hidden auto-selection.
- `Send`: executes one labelled stimulation trial only when backend source is ready; never stimulates automatically on page load.
- `Optimise`: executes candidate set on backend; shows actual per-trial progression, not a predetermined animation.
- `Source`: demo mode switching requires confirmation; source provenance persists in every displayed number.
- `Export`: downloads CSV/JSON report + PNG snapshot. Keep participant audio off by default; don't save raw speech unless necessary/consented.

### UI acceptance tests
- App usable on a 13-inch laptop and projected at 1080p without horizontal scroll.
- If microphone permission denied, buttons still work with no crash.
- If Python backend down, show "Disconnected" and disable send.
- If no neuron responses, show "Insufficient evidence" rather than high accuracy.
- Never show metrics for a run with unspecified source/provenance or n=0.
- Running `RESET` clears UI state but retains exported runs on disk.

---

## 6. SYSTEM ARCHITECTURE

```
Browser Mic / YES-NO buttons
             |
             v
Digital label selector (audio recognition or explicit button)
             |
             v
Encoder: label + theta -> sequence of safe stimulation requests
             |
             v
Hardware Abstraction Layer (NeuralBackend)
     |                 |                 |
 REACTIVE_SIM       REPLAY          CL1_LIVE
     |                 |                 |
     +-----------------+-----------------+
                       |
                Raw voltage / spikes
                       |
        Artifact mask + stimulus-timed epochs
                       |
             Features (spikes / PSD)
                       |
         Decoder (fit on training trials only)
                       |
    Validation scores + experimental controls
                       |
        Optimiser chooses candidate theta
                       |
     LOCK ENCODER -> fresh held-out TEST trials
                       |
             Dashboard + run export
```

### Source interfaces (Python Protocol/pseudocode)
```python
@dataclass(frozen=True)
class StimPulse:
    channel: int
    offset_ms: float
    phase_us: int             # per phase, must be valid per CL1 API
    current_uA: float        # magnitude; biphasic sign generated by adapter

@dataclass
class Trial:
    trial_id: str
    run_id: str
    source: Literal['reactive_sim','replay','live_cl1']
    label: Literal['YES','NO']
    encoder_id: str
    encoder_params: dict
    stimulus: list[StimPulse]
    stim_begin_us: int | None
    stim_end_us: int | None
    raw_samples: np.ndarray | None  # (samples, channels), when available
    spikes: list[dict]              # timestamp/channel, when available
    response_window_ms: tuple[float,float]
    artifact_intervals_ms: list[tuple[float,float]]
    features: np.ndarray | None
    pred_label: str | None
    pred_prob: float | None
    split: Literal['train','val','test','control']
    metadata: dict                  # device config, seed, active channels, etc.

class NeuralBackend(Protocol):
    def get_status(self) -> dict: ...
    def connect(self) -> None: ...
    def run_trial(self, pulses: list[StimPulse], trial_id: str) -> Trial: ...
    def close(self) -> None: ...
```

**Important:** The replay adapter can evaluate only the stimulation protocol actually used to generate those recordings. It cannot provide genuine counterfactual neural responses to new electrode patterns. For different encoders it must have separate real recorded trials per encoder, or the UI must disable claiming experimental comparison.

### Suggested endpoints
- `GET /health` -> backend + source + device readiness
- `GET /config` -> supported source, channels, safety gate, feature configuration
- `POST /audio/label` optional; frontend can handle microphone classification
- `POST /trials` -> class, encoder_id; asynchronously enqueue trial; return job id
- `GET /trials/{id}` -> result + provenance
- `POST /experiments/calibration` -> queue counterbalanced repeated trials
- `POST /experiments/optimise` -> evaluate pre-specified candidates
- `POST /experiments/lock-test` -> freeze model/encoder and acquire held-out trials
- `GET /experiments/{id}/report` -> metrics, controls, sample sizes, CI, provenance
- `GET /experiments/{id}/export` -> CSV + JSON
- `WS /events` -> progress, stimulation, spike batch, model predictions, errors

Keep real-time CL1 loop synchronous/time-critical in a dedicated thread/process; never run frontend plots or heavyweight training inside its time-sensitive callback.

### Repository layout
```
neurohear/
  README.md
  SPEC.md
  .env.example
  pyproject.toml
  backend/
    app.py
    schema.py
    acquisition/
      base.py
      cl1_adapter.py
      simulator_adapter.py
      replay_adapter.py
    encoding/
      rate.py
      temporal.py
      safety.py
    experiment/
      scheduler.py
      protocols.py
      feature_extract.py
      decoder.py
      optimiser.py
      metrics.py
      controls.py
      persistence.py
    simulations/
      reactive_source.py
  frontend/
    package.json
    src/
      App.tsx
      components/Microphone.tsx
      components/PulseMatrix.tsx
      components/NeuralRaster.tsx
      components/OptimiserPanel.tsx
      components/QualityControl.tsx
      lib/api.ts
  tests/
    test_encoder.py
    test_safety.py
    test_split.py
    test_artifact.py
    test_simulation_no_label_leak.py
    test_controls.py
    test_api.py
  artifacts/
    sample_report.json
    preflight_demo.mp4   # clearly captioned SIMULATED if created
  scripts/
    run_local.sh
    smoke_test.sh
```

---

## 7. ENCODER DESIGN — DELIBERATELY MINIMAL

**Input classes:** binary YES vs NO. The labels are digital tags; the label is not passed to any downstream model except scoring. A deterministic encoder converts the label into a stimulation schedule. The readout decoder only sees neural signals.

### Candidate A — Rate code
Fixed channel set and time window. Two pulse-spacing templates represent the binary labels by relative rate. Keep matched total pulses across classes if feasible; if rate differs by class, note stimulus burden/confounding and avoid overclaiming. Label-to-template mapping is fixed and logged.

### Candidate B — Timing/phase code (recommended main candidate)
Use the **same number of pulses, current, channels, and overall duration** as A; differentiate YES from NO using precisely logged temporal arrangement/channel order. This makes comparisons cleaner under matched stimulation burden. Keep it simple (2–4 channels, a few pulses, a sub-second sequence) and check device compatibility.

### Optimisation parameters
Predefine only **3–5** candidate settings. Parameters to search (choose one or two, not all):
- separation between pulses;
- choice of electrode group (only if operator-approved);
- inter-group phase shift;
- coarse pattern geometry.
**Do not optimise current, pulse width, number of high-rate pulses or other risky physical parameters without explicit operator permission.** Default optimiser varies timing patterns at fixed charge budget.

### CL1-specific API
Official developer guide https://docs.corticallabs.com/ ; API reference https://docs.corticallabs.com/cl ; simulator https://docs.corticallabs.com/cl/sim ; repo https://github.com/Cortical-Labs/cl-sdk.
- `pip install cl-sdk` and test local `cl.open()` with in-process simulator.
- Real/Simulator control API uses `with cl.open() as neurons`, `neurons.stim(ChannelSet(...), StimDesign(...))`, and `neurons.loop(...).analysis.spikes` or `read()`.
- Sample/frame time uses 25,000 Hz in the simulator's custom data-source API.
- Documented `StimDesign` pulse widths must be positive multiples of 20 μs; max absolute phase current 3.0 μA and total charge max 3.0 nC; `BurstDesign` burst frequency max 200 Hz. **These are SDK constraints, not a clinical safety certification or approval for any culture.** Lab operator must specify much tighter allowed values as relevant.
- `cl.sim.set_simulator_data_source('backend.simulations.reactive_source:create_source', config={'seed': 123, ...}, metadata=...)` creates model that handles `on_stim` and supplies `DataSourceBatch`. This custom simulation is **only for rehearsal and software integration**. Default random SDK simulator *does not model neuronal response to stims*.
- Query current SDK signatures at implementation time and verify sample code against docs. No assumption that a physical device will be accessible.

### Stim safety gates
- No stimulation without physical operator approval and explicit runtime `LIVE_STIM_ENABLED=true` interlock.
- Server hard-clamps current, duration, number of pulses, allowed channels, inter-trial refractory interval and total-session stim count; fail closed if hardware limits are unconfigured.
- Extra UI confirmation before the first live stimulation; visible STOP button calls device interruption function where supported.
- Audit every stimulation command, whether delivered or rejected.
- No default 'safe' live pulse setting. Start in read-only live mode; lab operator supplies constraints.

---

## 8. SIMULATOR SPECIFICATION — MUST BE HONEST AND NON-TRIVIAL

### Two simulator modes
1. `cl-sdk random`: produces synthetic control spikes independent of stimulation. Expected to be at chance under correctly held-out balanced decoding. Use as a **negative control**.
2. `reactive_sim`: custom stimulation-responsive, non-learning **mathematical model** used to test end-to-end mechanics and adaptive selection. It should produce spike/voltage responses to actual committed stim events. Data source must not receive labels, encoding IDs or optimiser fitness scores. It only sees event timestamp, channel and pulse parameters. Seed recorded in metadata.

### Reactive model sketch
For output channel j and poststim time t:
```
rate_j(t) = baseline_j
          + sum_over_stim_events k [gain[j, stim_channel(k)]
             * kernel(t - event_time(k) - delay[j,k])]
          + network_noise_j(t)
```
- `kernel(dt)` causal (zero before dt=0), e.g. alpha-like transient decay.
- `gain` a fixed, seeded sparse random connectivity matrix with some inhibitory/saturating dynamics if desired.
- `network_noise` includes spontaneous Poisson/recurrent spikes and slow drift.
- artifact overlay on voltages can be injected at stimulation time but must be masked before any decoder feature extraction.
- Add a configurable `gain=0` control: response must revert to chance on held-out trials, within sampling error.
- The mathematical model may favour some temporal patterns; disclose that this behaviour is **by model construction**, not a discovered biological effect.

### Simulator validation
- Same input pulse schedule and same seed produce bitwise-identical output where possible.
- Changing the label without changing the pulse schedule does **not** change neural response.
- Shuffling the training labels drops held-out balanced classification to approximately chance.
- Disabling model response removes class-specific information from the response features.
- Artifact mask excludes every pulse and specified postpulse blank interval.
- The training/validation/test split never shares one trial (or bins from it) across subsets.

---

## 9. TRIALS, FEATURES, DECODERS AND METRICS

### Trial protocol
A trial contains: (a) digital label; (b) fixed encoder ID; (c) stimulation event schedule; (d) time-aligned neural recording; (e) artifact mask; (f) poststim response; (g) feature vector; (h) split and metadata.
- Use the same response window and feature extraction across encoder conditions.
- Begin with **10 ms after the final pulse** and consider a 400 ms poststim feature window, as used in Loeffler, subject to CL1 timing and actual artifact recovery. Exclude a longer interval if needed, or fail the quality gate if no clean segment remains.
- Randomise class order and candidate order; interleave condition blocks to reduce confounding from neural drift. Do not compare two protocols acquired in systematically different substrate states without qualification.
- Pre-assign train/validation/test **before collecting**, with balanced labels and a fixed random seed. No peeking at test labels during tuning.
- If too few trials/active electrodes, show descriptive response plots rather than false claims of decoding superiority.

### Starter sampling (planning assumption, adjust on site)
- Preflight 5–10 min: baseline spontaneous activity, check functioning electrodes and preliminary responses.
- Candidate search: 3 candidate protocols × 2 labels × 8 training + 4 validation trials per label = **72 calibration trials**.
- Lock best candidate from validation; compare baseline and chosen candidate on **10 new independent held-out trials per label per condition** = **40 test trials**.
- Total roughly **112 experiments** plus rest/processing; at about 1–2 s including recording, this is a few minutes of acquisition but hardware scheduling, troubleshooting and culture variability can dominate. If impossible, decrease candidates/trials and label claims preliminary. **Never report a reliable biological gain on insufficient samples.**

### Feature extraction
**MVP:** channel-wise poststim spike counts, coarse bins, latency to first poststim spike, simple firing rate difference from pretrial baseline; robust normalisation fitted only on training data.
**Recommended PSD track when raw voltages exist:** FFT/Welch band-power summaries across channels on a clean 400 ms poststim epoch; band definitions appropriate to available sampling/resolution. Use log-power, optionally dimension reduction fitted on training data. Keep frequency-domain complexity modest for short trials.
**Quality checks:** missing channels, saturation, artifacts, too few spikes, overly high no-stim activity, source timestamps, alignment error, trial dropout.

### Decoder
- Start with standardised, regularised logistic regression with class weights only if needed, trained on trial-level features.
- Fit scaler and decoder exclusively to training trials; choose hyperparameters and encoder using validation; run **once** on sealed test set.
- Optional random forest on PSD features if enough trials; do not use high-capacity models to force artificial accuracy on tiny samples.
- For data with high trial-to-trial variance, show average performance across repeated trials instead of making a single lucky demonstration the proof.

### Reported primary metric
- **Held-out balanced accuracy**, correct out of N with exact count shown, plus permutation-label negative-control accuracy.
- Confidence interval where feasible; for tiny samples, show uncertainty prominently.
- A separability metric (e.g. cross-validated decoding advantage vs permuted labels), secondary to accuracy.
- Pulse count/total absolute charge/current-weighted budget matched across A/B; show counts, no claim of clinical energy use.
- Show change vs fixed baseline (percentage points) only with N, data source, randomisation and controls.

### Important conceptual baseline
The software encoder itself knows which stimulus it sent; a digital decoder of the pulse train can trivially recover that label. Thus **do not advertise better-than-silicon speech recognition**. A positive result here is that *poststim neuronal response carries stimulus-class information above matched controls*, or that a protocol improves **neural** readout separability for a fixed stim budget. To claim useful reservoir computation beyond simple transmission would require stronger input-only/null/reservoir ablation benchmarks, novel tasks and multiple cultures.

### Controls
Required for every run:
1. `PERMUTED_LABELS`: shuffle labels at trial level; expect chance-like evaluation in balanced classes.
2. `NO_RESPONSE`: SDK default/random/no-stim or reactive simulator with response disabled; expect chance.
3. `ARTIFACT_MASK`: predeclared exclusion of stimulation period and poststim blanking window.
4. `TRAIN_TEST_SEPARATION`: disjoint whole trials with frozen preprocessing.
When physical access exists, request operator-supported no-cell/media-only measurement. Do not fabricate a saline recording. If impossible, explicitly mark `not acquired`.

---

## 10. OPTIMISATION LOGIC

**Aim:** select the stimulation encoding that maximises validated separability with fixed permissible burden, not to induce synaptic learning.

For encoder parameter set theta:
```
score(theta) = balanced_accuracy_validation(theta)
             - alpha * stimulation_burden(theta)
             - beta * artifact_fraction(theta)
```
In v1, stimulation burden is approximately identical by construction, so score is primarily validation accuracy. Include failure penalties for poor signal quality. `alpha` and `beta` are explicit, not tuned against test.

Optimisation algorithm:
1. Fix allowable parameter grid beforehand (3–5 candidate sets).
2. Collect randomized labelled trials for each.
3. Fit identical pipeline per candidate on training trials.
4. Evaluate on validation trials; compare negative controls.
5. Lock candidate, decoder and preprocessing.
6. Acquire fresh *sealed* test trials for baseline and chosen strategy, with randomized order.
7. Show comparison and uncertainty. If ties/poor data, show "No demonstrated gain".

If a model is only replaying prerecorded activity from one protocol, **do not** claim adaptive optimisation of new protocols. Use purely offline feature/decoder comparison and label as such.

---

## 11. PRE-EVENT WORK VS ON-SITE TWO-HOUR WORK

**Big distinction:** engineering completion and experimental completion. The software can be substantially finished before arrival, *if the rules allow bringing code*. Genuine live neuronal findings cannot.

### PRE-EVENT: build + test before arriving (target 80–90% of engineering)
| Deliverable | Dependency | Acceptable pre-event finish criterion |
| --- | --- | --- |
| Frontend dashboard, microphone + fallback | Browser only | all interactions run locally |
| Pulse encoding and two strategies | none | deterministic and matched stimulation burden |
| Data protocol / trial schema / logging | none | complete JSON/CSV record for every trial |
| Reactive custom CL-SDK simulator | local `cl-sdk` | stims provoke model-dependent responses via API |
| Random/no-response negative controls | local simulator | balanced accuracy near chance |
| Artifact blanking and features | fixtures | known pulses removed; PSD/spikes tested |
| Train/validation/test splitting and decoder | fixtures | no same-trial leakage; correct metrics |
| Grid search optimiser | simulator | chooses best *validation* encoder, locks test |
| End-to-end smoke tests | localhost | end-to-end demo completes with no cloud |
| Explicit provenance labelling | entire app | screenshot clearly says simulated vs live |
| 3-slide pitch + offline contingency clip | none | truthful, accessible without internet |
| CL1 adapter skeleton (read-only by default) | SDK docs | import/contract tests, not assumed physically tested |

**Before arriving:** all of the UI, simulation pipeline, tests, report export, demo rehearsal, and pitch can be ready. **Not preparable honestly:** experimental neural responses to tomorrow's candidate protocols, real culture-specific optimal code, trial-specific performance, or proof of neuronal adaptation.

### ON-SITE: 19:30–21:30 executable sequence
- **19:00–19:30 (tutorial, before official build):** verify rules, access, operator protocol, sample recordings, headset/projector logistics; no unapproved work that violates event rules.
- **19:30–19:45 (15m):** environment check, backend/frontend smoke tests, identify source type, obtain stim permission, run source status and timestamps. `GO/NO-GO` for physical backend by 19:45.
- **19:45–20:05 (20m):** real calibration if hardware available: spontaneous activity, electrode viability, short safe test with operator. Otherwise simulator experiment with organiser-specific task constraint.
- **20:05–20:45 (40m):** run counterbalanced two-class trials for baseline and 2–3 candidate encoders, visualise responses, and test signal-quality gates. If real no signal, do not spend whole slot chasing impossible biology.
- **20:45–21:05 (20m):** validation optimisation, lock candidate, holdout tests, negative controls. Save results.
- **21:05–21:20 (15m):** freeze demo outputs, inspect artifact/label controls and provenance, prepare one-slide evidence table and reproduce result.
- **21:20–21:30 (10m):** rehearse pitch, fallback route, clean terminal, ensure internet/mic permissions.
- **21:30–22:00:** judge demos.

### Hard pivots
- By **19:45**, no live device: choose reactive-simulation mode; do not claim living-neuron evaluation.
- By **20:05**, device available but stim prohibited: use real baseline recording + simulator candidate optimisation, clearly shown as separate evidence streams.
- By **20:30**, real stim but no reliable evoked signal: retain genuine acquisition as pilot; use simulator for a successful software-loop demonstration.
- By **20:45**, no clean measurements: skip model training claims; demo acquisition/format/quality controls honestly.
- Never sacrifice tested provenance and backup for speculative new features.

### Estimate (subjective, contingent on rules/access)
- **80–90% of software engineering** can be ready beforehand.
- **0% of new event-specific physical CL1 experiments** can be prevalidated without hardware/recordings.
- **10–20% of code work on site** should be integration, troubleshooting and task-specific adaptation, with the majority of on-site time for data collection, validation and pitch.
- These are scope-planning percentages, not measurements or permission to bring prebuilt code.

---

## 12. AGENT DELEGATION — COPY AND ASSIGN

### Agent A — Frontend and showmanship
**Owner:** `frontend/` only.
**Task:** Build one-page projector-friendly React app showing input, pulse matrix, neural response, classifier prediction, optimisation metrics, experiment provenance. Implement push-to-talk (browser permission failures handled), YES/NO fallback, component skeleton + WebSocket subscription from published schema. Provide source badges and trial N on all metrics. Avoid any mock values that pretend to be measured outcomes. Use explicit `SIMULATED` labels for fixture values.
**Acceptance:** screenshot at 1920×1080 legible; microphone denied fallback works; click-through pitch replay works; no blocking on missing backend.

### Agent B — Signal and scientific validity
**Owner:** `backend/encoding/`, `backend/experiment/feature_extract.py`, `decoder.py`, `controls.py`, `metrics.py`, `tests/` scientific tests.
**Task:** Implement two matched-budget encoders, artefact masking, poststim spike feature and PSD feature path, leakage-safe trial split, logistic decoder, balancing/CI/negative controls. Unit tests must show no data leakage or label-dependent simulator shortcut.
**Acceptance:** runs on synthetic fixtures; null/no-response ≈ chance over repeated seeds; artifact-only fixtures fail quality gate; report includes N and provenance.

### Agent C — CL1 backend and reactive simulator
**Owner:** `backend/acquisition/`, `backend/simulations/`, `backend/encoding/safety.py`.
**Task:** Implement NeuralBackend Protocol; fully functioning stimulation-reactive model using `cl.sim.set_simulator_data_source`, supporting real stim events from `neurons.stim` and producing poststim spikes/frames; read-only `cl1_adapter.py` with explicit live-stim operator approval gate; import-safe when cl-sdk absent; route every trial through same schema.
**Acceptance:** local SDK smoke test, reactive model depends on stim events but not labels; correct 25k frame-time indexing; live stim impossible unless interlock explicitly enabled; status identifies source.

### Agent D — Integrator, experiments and pitch
**Owner:** `backend/app.py`, `backend/experiment/scheduler.py`, `optimiser.py`, `persistence.py`, scripts, SPEC, slide/pitch assets.
**Task:** Build job queue, experiment state machine and REST/WS endpoints; run tests across other agents; enforce train/validation/holdout; export truthful results; write 90-second demo script and one-slide experimental evidence summary.
**Acceptance:** from a fresh terminal, one-command launch plus end-to-end 5-minute dry run; no test contamination; backup recording works without internet.

### Safe parallel workflow
- Agree on schema and `NeuralBackend` interface FIRST; freeze types before splitting work.
- Agents work in separate directories/branches; integrator merges early.
- Agent B/C define common timestamps/units before writing data acquisition.
- Do not allow both frontend and backend agents to invent their own payload shapes.
- Integrate and run smoke test before adding visual polish.

---

## 13. EXPERIMENT STATE MACHINE AND API CONTRACT

State transitions:
```
IDLE -> READY -> CALIBRATING -> BASELINE -> OPTIMISING -> LOCKED_TEST -> REPORT_READY
                                \-> QUALITY_FAILED -> REPORT_READY
ANY -> ERROR -> READY (only after operator reset)
```
Safety conditions:
- No transition to `LIVE_STIM` without operator approval.
- Do not permit candidate change during `LOCKED_TEST`.
- Trial data immutable after acquisition. Processing transformations carry version hashes.
- Every run has UUID, data source, CL-SDK version, seed, electrode map, pulse parameters, and timestamps.

Suggested WebSocket events:
```json
{"type":"trial_started","trial_id":"uuid","source":"reactive_sim","encoder_id":"A"}
{"type":"stim_delivered","trial_id":"uuid","timestamp_us":1000000,"channel":8}
{"type":"spikes_batch","trial_id":"uuid","source":"reactive_sim","events":[{"t_ms":123.4,"channel":9}]}
{"type":"trial_result","trial_id":"uuid","pred_label":"YES","pred_prob":0.64,"artifact_masked":true}
{"type":"progress","state":"OPTIMISING","completed":36,"total":72}
{"type":"report_ready","run_id":"uuid","provenance":"SIMULATED MODEL"}
```

Suggested report fields: `run_id`, `timestamp`, `source`, `is_live`, `hardware_id`, `stim_approved_by` (optional operator identifier, no personal data needed in public report), `encoder_ids`, `params`, `samples_per_class`, `train_val_test_ids`, `primary_metric`, `confidence_interval`, `permutation_control`, `artifact_exclusion`, `no_cell_control_status`, `stimulation_budget`, `data_quality_flags`, `software_commit`, `notes`.

---

## 14. UNIT/INTEGRATION TESTS (DO THESE BEFORE THE EVENT)

**Safety:** Reject invalid channels/phase width/current/burst rate/session counts and all live-stim attempts without permission.
**Simulator causal contract:** response must be invariant to class label if pulse schedule identical; response must differ with different delivered stim when gain > 0.
**Artifact:** deliberately inject an electrical artifact correlated with class; including stim window inflates accuracy, masking removes that artifact-only advantage.
**Random/no-response:** shuffled-label and response-disabled model results are chance-like *over many seeds*; account for sampling fluctuations.
**Splitting:** no trial ID shared across train/validation/test; all feature normalisers fit on training set.
**Optimiser:** can't inspect test labels or test metrics until chosen candidate and decoder frozen.
**Replay:** refuses to claim effects of stimulation protocols absent in the recording.
**Provenance:** exported figures/reports include source, timestamp, N and whether live neuronal tissue was used.
**Fault-tolerance:** microphone denied; backend disconnected; no spikes; fewer than two classes; all electrodes saturated; invalid CL-SDK package; browser refreshing mid-session.
**Script:** `./scripts/smoke_test.sh` starts or probes services and runs a simulated calibration -> optimisation -> locked-test -> JSON export without editing code.

---

## 15. DEMO CLAIMS AND FAILURE-PROOF PITCH

### Valid claims (if actually demonstrated)
- "We've built a software pipeline that translates discrete human commands into electrical stimulation codes and measures biological or simulated neural responses."
- "Our optimiser searches for more distinguishable neural response patterns at a controlled stimulation budget."
- "Our test protocol explicitly guards against stimulation artifact and train/test leakage."
- "On these live culture trials, the chosen encoder showed X correct out of N held-out trials; negative control Y." (only if true)

### Invalid claims
- "The cells can hear or understand speech."
- "The cells learned language" or "the neurons improved" if software optimisation alone improved.
- "NeuroHear improves cochlear implant outcomes" (no appropriate anatomy/patient trial).
- "The biological computer beats digital speech recognition" (the digital label is known before stimulation).
- "Real neurons were tested" in simulator-only mode.
- "Stimulation optimisation succeeded" when only a reactive model with built-in preference was shown.

### A pitch that works even if simulator-only
"Cortical Labs and Frontier Computing are making biological compute programmable. Yet today, there is no universal way to speak to each living neural network: an electrical code that works well in one culture may fail in another. We built NeuroHear, an experiment engine that takes a simple digital message, compiles it into electrical pulses, measures the resulting neural response, and searches for the most distinguishable response under a fixed stimulus budget. Our demo runs against a declared stimulation-responsive model today, with artifact and label controls; the next experiment is a real CL1 culture, where we can validate whether these improvements hold in biology. The bigger opportunity is adaptive I/O for biological compute, with future research applications in neural prostheses."

### A stronger pitch if live data validates
Same intro, then replace "model" with "a live CL1 culture" and show actual trial-count results and negative controls. Never claim generic or clinical efficacy from one culture.

### Three-slide deck structure
1. **Problem:** biological processors need an adaptable electrical I/O language. Big show of mic -> pulses -> chip.
2. **Proof:** a live or properly labelled simulated raster; baseline vs selected encoder; N, uncertainty, artifact/permutation controls.
3. **Vision:** hardware-independent neural protocol optimiser: Cortical Labs-compatible now, future biological computing and neuroprosthetics research. Explicit next experiments: 3+ cultures, robustness, long-term drift and real electrode comparisons.

---

## 16. RISKS / FALLBACKS

| Risk | Probability/impact | Mitigation / fallback |
| --- | --- | --- |
| No CL1 access | High impact, unclear likelihood | reactive simulator, factual provenance, pitch as tool for CL1-day prize |
| Prebuild banned | Compliance-critical, unknown | confirm rules; follow permitted reuse limits and honest attribution |
| No spike response on live culture | High potential impact | report failure honestly; simulator showcases software only |
| Stim artifacts drive accuracy | High scientific impact | exclude full stim window + blank; saline/no-cell if available |
| Class readout uses label leakage | High integrity impact | generator sees only pulse events; train/test separated by trial |
| Tiny held-out dataset | High statistical impact | count-based results, uncertainty, no overclaim |
| Mic fails in loud room | Medium | YES/NO buttons + labelled prerecorded samples |
| SDK import/OS mismatch | Medium | tested pure-Python fallback adapter + pinned requirements |
| Real-time callback freezes | Medium/high | separate hardware worker from UI/backend learning |
| Optimiser overfits to validation | Medium | small fixed candidate set and sealed holdout |
| Confusion about cochlear clinical applicability | High credibility impact | position as neural I/O benchmark, not actual cochlear model |

---

## 17. STOP/GO DECISIONS

**GO for a competitive entry if:** end-to-end pipeline works, source truthfulness is visible, two encoders can be compared on valid trials (simulated or live with explicit provenance), controls are implemented, and a judge can intuitively understand what the neural activity adds to the experiment.

**DO NOT make a biological optimisation claim if:** no live culture or relevant recorded data, no artifact-clean responses, or no independent held-out evaluation.

**Do not add more classes or complex speech recognition** until binary, simulator integration and negative controls work reliably.

---

## 18. SOURCE LINKS / VERIFICATION

- Event: https://luma.com/2khmpnqp
- CL1 hardware: https://corticallabs.com/cl1
- CL1 docs: https://docs.corticallabs.com/
- CL API: https://docs.corticallabs.com/cl
- Simulator data-source API: https://docs.corticallabs.com/cl/sim
- SDK: https://github.com/Cortical-Labs/cl-sdk
- Callosum: https://www.callosum.com/
- Frontier Computing: https://frontier.site/
- Smirnova & Hartung (2022): https://doi.org/10.1016/j.neuron.2022.11.010
- Original DishBrain primary study: https://pmc.ncbi.nlm.nih.gov/articles/PMC9747182/
- Robbins et al. (2026): https://doi.org/10.1016/j.celrep.2026.116984
- Loeffler et al. (2026) preprint: https://doi.org/10.64898/2026.08.10.743829

---

## 19. ONE MASTER PROMPT FOR A CODING AGENT

> You are the lead engineer of NeuroHear, a neuroscience hackathon demonstration for Outlier Labs × Project A on 3 November 2026. Read this entire specification as binding scope. Implement the P0 system as an honest stimulation-responsive *simulator-based* application first; do not assume physical access to CL1. Use a Python/FastAPI backend, `cl-sdk` custom simulation data source when available, and React/TypeScript dashboard. A digital YES/NO command is encoded into electrical pulse events; a reactive mathematical neural model responds only to those events; a leakage-safe classifier reads artifact-masked poststim features; an optimiser compares a tiny set of stimulation patterns on validation trials and then locks a candidate for independent held-out testing. Implement negative controls and show the data-source badge on every result. Prioritise end-to-end reliability, scientific integrity, repeatability, and export over advanced ML. Do not fake living-neuron measurements, run stimulation without explicit operator approval, or claim biological learning. Split work into modules following the repository and interface contracts above; add tests before shipping UI polish. The first milestone is a one-command startup and a 5-minute fully repeatable simulated demo. Produce actual working code and concise run instructions, not mock-only screens.

