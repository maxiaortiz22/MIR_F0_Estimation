from __future__ import annotations

from .AutocorrEstimator import AutocorrEstimator
from .BaseF0Estimator import BaseF0Estimator
from .PyYINEstimator import PyYINEstimator


def create_estimator(name: str) -> BaseF0Estimator:
    """Create an F0 estimator by name.

    Heavy optional estimators are imported lazily so that lightweight demos can
    still run when a neural estimator dependency is not installed.
    """
    key = name.lower()
    if key in {"autocorr", "autocorrelation"}:
        return AutocorrEstimator()
    if key in {"pyin", "p_yin"}:
        return PyYINEstimator()
    if key == "crepe":
        from .CrepeEstimator import CrepeEstimator

        return CrepeEstimator()
    if key in {"swiftf0", "swift_f0", "swift"}:
        from .SwiftF0Estimator import SwiftF0Estimator

        return SwiftF0Estimator()
    raise ValueError("Unknown method. Use one of: autocorr, pyin, crepe, swiftf0")
