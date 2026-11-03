"""Primary metric: held-out balanced accuracy with exact counts and an exact
(Clopper-Pearson) 95% CI on raw accuracy. Small-N uncertainty shown honestly."""
from __future__ import annotations

from scipy.stats import beta
from sklearn.metrics import balanced_accuracy_score


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return float(lo), float(hi)


def score(y_true: list[str], y_pred: list[str]) -> dict:
    n = len(y_true)
    if n == 0 or len(set(y_true)) < 2:
        return {"n": n, "correct": int(sum(a == b for a, b in zip(y_true, y_pred))),
                "balanced_accuracy": None, "accuracy": None, "ci95": None,
                "status": "insufficient_evidence"}
    k = int(sum(a == b for a, b in zip(y_true, y_pred)))
    return {"n": n, "correct": k, "accuracy": k / n,
            "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
            "ci95": clopper_pearson(k, n), "status": "ok"}
