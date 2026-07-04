from .BaseF0Estimator import BaseF0Estimator, F0Result
from swift_f0 import SwiftF0, PitchResult  # noqa: F401  (for type hints / validation)
import numpy as np


class SwiftF0Estimator(BaseF0Estimator):
    """SwiftF0 wrapper using the official swift-f0 package API."""

    def __init__(self, fmin_hz: float = 46.875, fmax_hz: float = 2093.75, confidence_threshold: float = 0.9):
        self.fmin_hz = fmin_hz
        self.fmax_hz = fmax_hz
        self.confidence_threshold = confidence_threshold

        # Keep a handle to the detector instance
        from swift_f0 import SwiftF0  # type: ignore
        self._detector = SwiftF0(
            fmin=self.fmin_hz,
            fmax=self.fmax_hz,
            confidence_threshold=self.confidence_threshold,
        )

    def estimate(self, y: np.ndarray, sr: int) -> F0Result:
        # SwiftF0 handles resampling to 16 kHz internally (requires librosa)
        result = self._detector.detect_from_array(y.astype(np.float32), sr)
        # Map to our neutral result object; mark unvoiced frames as NaN
        f0 = np.asarray(result.pitch_hz, dtype=float)
        times = np.asarray(result.timestamps, dtype=float)
        # If voicing is present, mask low-confidence frames
        if hasattr(result, "voicing") and result.voicing is not None:
            mask = np.asarray(result.voicing).astype(bool)
            f0 = np.where(mask, f0, np.nan)
        return F0Result(f0_hz=f0, times_s=times)