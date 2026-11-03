# NeuroHear evidence — SIMULATED MODEL

Run `20261103-202617-371a1b` · seed 123 · living tissue: **False**

| Condition | Held-out correct | Balanced acc. | 95% CI (acc.) |
|---|---|---|---|
| A_rate (baseline) | 11/20 | 0.55 | 0.32–0.77 |
| B_order_ipi60 (chosen) | 20/20 | 1.00 | 0.83–1.00 |

**Permuted labels:** null mean 0.51, 95th pct 0.80, p = 0.005 (n_perm=200)
**No-response control:** 24/40 masked (bal. acc 0.60, binomial p vs chance 0.13); unmasked 1.00
**Artifact mask:** 5.0 ms blank/pulse, window starts 10.0 ms after final pulse, 400.0 ms long. Without mask (diagnostic): 1.00
**No-cell/saline control:** not acquired

**Verdict:** Chosen encoder outperformed baseline on sealed held-out trials (see N, CI, controls).

- Calibration blocks: baseline acquired first, other candidates interleaved; the sealed test interleaves baseline and winner.
- The digital label is known before encoding; a decoder of the pulse train would be trivially perfect. Results concern information in the post-stimulus NEURAL response only.
- No claim of speech understanding, hearing, or biological learning.
- SIMULATED: encoding preferences exist by model construction, not as a biological finding.
