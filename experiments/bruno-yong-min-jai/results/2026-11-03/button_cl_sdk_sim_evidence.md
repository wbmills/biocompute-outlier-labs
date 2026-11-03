# NeuroHear evidence — SIMULATED MODEL VIA CL-SDK

Run `20261103-211045-cbb4d4` · seed 123 · living tissue: **False**

| Condition | Held-out correct | Balanced acc. | 95% CI (acc.) |
|---|---|---|---|
| A_rate (baseline) | 12/20 | 0.60 | 0.36–0.81 |
| B_order_ipi60 (chosen) | 20/20 | 1.00 | 0.83–1.00 |

**Permuted labels:** null mean 0.50, 95th pct 0.80, p = 0.005 (n_perm=200)
**No-response control:** not acquired
**Artifact mask:** 5.0 ms blank/pulse, window starts 10.0 ms after final pulse, 400.0 ms long. Without mask (diagnostic): 1.00
**No-cell/saline control:** not acquired

**Verdict:** Chosen encoder outperformed baseline on sealed held-out trials (see N, CI, controls).

- Calibration blocks: baseline acquired first, other candidates interleaved; the sealed test interleaves baseline and winner.
- The digital label is known before encoding; a decoder of the pulse train would be trivially perfect. Results concern information in the post-stimulus NEURAL response only.
- No claim of speech understanding, hearing, or biological learning.
- SIMULATED: encoding preferences exist by model construction, not as a biological finding.
