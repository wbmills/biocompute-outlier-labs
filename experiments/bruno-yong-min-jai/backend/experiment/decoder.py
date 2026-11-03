"""Leakage-safe trial-level decoder: standardiser + L2 logistic regression,
both fitted on TRAINING trials only. Frozen after fit."""
from __future__ import annotations

import hashlib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

DECODER_VERSION = "logreg-l2-C0.05-v1"


class Decoder:
    def __init__(self, C: float = 0.05):
        self.C = C
        self.scaler: StandardScaler | None = None
        self.clf: LogisticRegression | None = None
        self.frozen = False
        self.train_ids: list[str] = []

    def fit(self, X: np.ndarray, y: list[str], trial_ids: list[str]) -> "Decoder":
        if self.frozen:
            raise RuntimeError("decoder is frozen")
        if len(set(y)) < 2:
            raise ValueError("training data must contain both classes")
        self.scaler = StandardScaler().fit(X)
        Xs = np.nan_to_num(self.scaler.transform(X))
        self.clf = LogisticRegression(C=self.C, max_iter=5000).fit(Xs, y)
        self.train_ids = list(trial_ids)
        return self

    def freeze(self) -> "Decoder":
        self.frozen = True
        return self

    def predict(self, X: np.ndarray) -> tuple[list[str], np.ndarray]:
        Xs = np.nan_to_num(self.scaler.transform(np.atleast_2d(X)))
        proba = self.clf.predict_proba(Xs)
        idx = proba.argmax(1)
        labels = [self.clf.classes_[i] for i in idx]
        return labels, proba.max(1)

    def fingerprint(self) -> str:
        h = hashlib.sha256()
        h.update(DECODER_VERSION.encode())
        h.update(self.scaler.mean_.tobytes())
        h.update(self.clf.coef_.tobytes())
        return h.hexdigest()[:12]
