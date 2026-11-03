# NeuroHear planted-learning positive control

**SIMULATED · planted STDP rule (positive control) · not biological evidence**

Input `B_order_ipi20` on groups A (8, 9) / B (18, 19); readout groups Y (34, 35), N (36, 37); hint 4 ms after the last input pulse; STDP learning rate 2.0. Seeds [123, 124, 125, 126, 127]; 20 probe trials per block per seed (N = 100 per point).

| Condition | First block | Last block | Last block per seed |
|---|---|---|---|
| contingent | 48% | 52% | 60, 50, 50, 60, 40 |
| sham | 46% | 48% | 50, 50, 55, 30, 55 |
| plasticity off | 49% | 49% | 55, 45, 60, 35, 50 |

**Pre-registered rule:** contingent last-block accuracy exceeds both sham and plasticity-off by >= 15 points, averaged over seeds. Smallest margin: 3 points. **DID NOT PASS.**

- The positive control FAILED: with this design the protocol did not detect the planted learning, so we cannot yet claim it would detect learning in real cells. It says nothing about real neurons.
- One tuning pass was made after the first run failed (hint 10 -> 4 ms, learning rate 0.5 -> 2.0). Diagnosed cause of the failure: non-selective potentiation (adjacent Y/N groups and inputs that already drive channel 36 directly).
- The model never receives labels: only pulses (inputs and hint) and its own spikes drive the rule.
