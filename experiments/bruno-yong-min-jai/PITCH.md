# NeuroHear: 90-second pitch

Say "simulated" out loud whenever the badge says it. Swap in live numbers only if they exist.

**0–10 s.** Hand a judge the mic: "Say yes or no." → *"The microphone is ordinary software. The interesting part starts now."*

**10–20 s.** Point at the pulse matrix. *"That word is now an electrical code: same pulses, same charge for yes and no — only the order and timing differ."*

**20–35 s.** Send. Point at the raster. *"Magenta is stimulation. The hatched bands are thrown away because stimulation artifacts can fake a result. The decoder only sees the shaded window, 10 ms after the last pulse."*

**35–50 s.** *"The decoder never sees the label. It reads the response and guesses."* Show prediction vs truth.

**50–70 s.** Optimise. *"Different cultures may prefer different codes. We pre-registered four candidates, trained on one set of trials, picked the winner on another, froze everything, then tested on trials nobody had seen."*

**70–85 s.** Cards + controls. *"On this simulated model, run through the Cortical Labs SDK simulator: baseline 12 of 20, chosen code 20 of 20. Shuffled labels sit at chance. On a simulated source whose spikes ignore stimulation we get 10 of 20 and the optimiser keeps the baseline. And without the artifact mask we'd score 100%, which is exactly the trap we guard against. The model prefers this code by construction; whether a real culture does is the experiment we want to run on a CL1."*
(Numbers: `cl_sdk_sim` and `sdk_random`, seed 123, 3 Nov, fresh server with nothing clicked first. On `cl_sdk_sim`, earlier clicks change
later results, so say what the cards show. If you demo the `reactive_sim` fallback, say 11 of 20 → 20 of 20 instead.)

**85–90 s.** *"Biological computers need an I/O layer that adapts to each culture. NeuroHear is that experiment engine. It runs on the Cortical Labs SDK simulator today; hardware is next."*

## Three slides

1. **Problem** — living processors need an electrical language that fits each culture. Mic → pulses → chip.
2. **Proof** — raster screenshot; baseline vs chosen with N and CI; permutation, no-response and artifact controls (`artifacts/sample_evidence.md`). Provenance badge visible.
3. **Next** — run on a live CL1 culture; 3+ cultures; drift across sessions; electrode-site search with operator approval. Long-term research angle: neural prosthesis coding.
   Cite Smirnova & Hartung 2022 (10.1016/j.neuron.2022.11.010), Robbins et al. 2026 (10.1016/j.celrep.2026.116984), Loeffler et al. 2026 preprint (10.64898/2026.08.10.743829).

## Claims

Valid (if shown): pipeline from command → stimulation code → measured response; optimiser finds more
distinguishable responses at fixed stimulation budget; protocol guards against artifact and leakage;
"X of N held-out trials, controls Y" with the source named.

Never: cells hear or understand speech; neurons learned; beats speech recognition (the label is known before
encoding); cochlear-implant or clinical benefit; "real neurons" in simulator mode; "optimisation succeeded in
biology" from a model with built-in preferences.

## If something breaks

- No mic / noisy room → Yes/No buttons (same path).
- No live device → stay on *Reactive model*, say so.
- Live device, no stim permission → *Record spontaneous activity* on hardware (read-only), simulator for the loop; present as two separate evidence streams.
- Laptop dies → `artifacts/preflight_demo_SIMULATED.mp4` (captioned) + `artifacts/sample_evidence.md`.
