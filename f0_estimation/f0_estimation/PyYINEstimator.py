from .BaseF0Estimator import BaseF0Estimator, F0Result
import numpy as np
import librosa


class PyYINEstimator(BaseF0Estimator):
    def __init__(
        self,
        frame_length: int = 2048,
        hop_length: int = 256,
        fmin_hz: float = 196.0,
        fmax_hz: float = 2000.0,
        center: bool = True,
        fill_unvoiced_with_nan: bool = True,
    ):
        self.frame_length = frame_length
        self.hop_length = hop_length
        self.fmin_hz = fmin_hz
        self.fmax_hz = fmax_hz
        self.center = center
        self.fill_unvoiced_with_nan = fill_unvoiced_with_nan

    def estimate(self, y: np.ndarray, sr: int) -> F0Result:
        f0, voiced_flag, voiced_prob = librosa.pyin(
            y,
            fmin=self.fmin_hz,
            fmax=self.fmax_hz,
            sr=sr,
            frame_length=self.frame_length,
            hop_length=self.hop_length,
            center=self.center,
        )
        # librosa.pyin returns np.ndarray with NaNs where unvoiced
        times = librosa.times_like(f0, sr=sr, hop_length=self.hop_length, n_fft=self.frame_length)
        if not self.fill_unvoiced_with_nan:
            f0 = np.nan_to_num(f0, nan=0.0)
        return F0Result(f0_hz=f0.astype(float), times_s=times.astype(float))