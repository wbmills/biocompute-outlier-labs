"""Negative controls.

PERMUTED_LABELS: refit the identical pipeline on training data with shuffled
labels, evaluate on the same held-out trials; repeat n_perm times. Gives a null
distribution and a permutation p-value for the observed held-out score.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import balanced_accuracy_score

from backend.experiment.decoder import Decoder


def permutation_control(Xtr, ytr, Xte, yte, observed: float | None, *, n_perm: int = 200,
                        seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    ytr = np.asarray(ytr)
    null = []
    for _ in range(n_perm):
        yp = rng.permutation(ytr)
        if len(set(yp)) < 2:
            continue
        d = Decoder().fit(Xtr, list(yp), [])
        pred, _ = d.predict(Xte)
        null.append(balanced_accuracy_score(yte, pred))
    null = np.array(null)
    p = None if observed is None else float((1 + (null >= observed - 1e-12).sum()) / (1 + len(null)))
    return {"name": "PERMUTED_LABELS", "n_perm": int(len(null)),
            "null_mean": float(null.mean()), "null_p95": float(np.percentile(null, 95)),
            "observed": observed, "p_value": p,
            "expectation": "chance-like (~0.5) null; observed must exceed null_p95 to claim separability"}
