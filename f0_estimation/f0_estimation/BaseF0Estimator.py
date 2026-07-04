from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class F0Result:
    f0_hz: np.ndarray  # shape: (n_frames,), NaN indicates unvoiced/unknown
    times_s: np.ndarray  # shape: (n_frames,)


class BaseF0Estimator(ABC):
    """Abstract base class for F0 estimators."""

    @abstractmethod
    def estimate(self, y: np.ndarray, sr: int) -> F0Result:
        """Estimate F0 contour for a mono signal.

        Parameters
        ----------
        y : np.ndarray
            Mono audio signal in float32/float64 range [-1, 1].
        sr : int
            Sampling rate in Hz.
        """
        ...
