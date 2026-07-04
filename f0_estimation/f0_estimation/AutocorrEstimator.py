from .BaseF0Estimator import BaseF0Estimator, F0Result
import numpy as np


class AutocorrEstimator(BaseF0Estimator):
    def __init__(
        self,
        frame_length: int = 2048,
        hop_length: int = 256,
        fmin_hz: float = 196.0,   # ~ G3 (violin open G string)
        fmax_hz: float = 2000.0,  # conservative upper bound for violin fundamentals
        center: bool = True,
    ):
        self.frame_length = frame_length
        self.hop_length = hop_length
        self.fmin_hz = fmin_hz
        self.fmax_hz = fmax_hz
        self.center = center

    def frame_timestamps(self, n_frames: int, hop_length: int, sr: int) -> np.ndarray:
        """Return timestamps (seconds) for each analysis frame given hop_length and sr."""
        return (np.arange(n_frames) * hop_length) / float(sr)

    def estimate(self, y: np.ndarray, sr: int) -> F0Result:
        y = np.asarray(y, dtype=float)
        # Optionally center-pad like STFT
        if self.center:
            pad = int(self.frame_length // 2)
            y_proc = np.pad(y, (pad, pad), mode="reflect")
        else:
            y_proc = y

        n = len(y_proc)
        f0s = []
        frames = range(0, n - self.frame_length + 1, self.hop_length)

        # Convert frequency bounds to lag bounds (in samples)
        max_lag = int(sr / self.fmin_hz)
        min_lag = int(sr / self.fmax_hz)
        min_lag = max(1, min_lag)

        window = np.hanning(self.frame_length)

        for start in frames:
            frame = y_proc[start : start + self.frame_length]
            if frame.size < self.frame_length:
                break
            x = frame * window
            x = x - x.mean()
            # Autocorrelation via FFT convolution for speed
            # rxx[k] = sum_n x[n] * x[n-k]
            fft_size = 1
            while fft_size < 2 * self.frame_length:
                fft_size <<= 1
            X = np.fft.rfft(x, n=fft_size)
            rxx = np.fft.irfft(X * np.conj(X), n=fft_size)
            rxx = rxx[: self.frame_length]

            # Normalize (peak at lag 0 to 1.0)
            if rxx[0] > 0:
                rxx = rxx / rxx[0]

            # Search for the best peak in valid lag range
            search = rxx[min_lag : max_lag]
            if search.size == 0:
                f0s.append(np.nan)
                continue
            lag = np.argmax(search) + min_lag

            # Parabolic interpolation for sub-sample peak refinement
            if 1 <= lag < len(rxx) - 1:
                alpha, beta, gamma = rxx[lag - 1], rxx[lag], rxx[lag + 1]
                denom = alpha - 2 * beta + gamma
                if denom != 0:
                    p = 0.5 * (alpha - gamma) / denom
                else:
                    p = 0.0
                lag = lag + p
            f0 = sr / lag if lag > 0 else np.nan

            # Basic voicing check: require autocorr peak above threshold
            if np.isnan(f0) or f0 < self.fmin_hz or f0 > self.fmax_hz or (search.max() < 0.2):
                f0s.append(np.nan)
            else:
                f0s.append(float(f0))

        n_frames = len(f0s)
        times = self.frame_timestamps(n_frames, self.hop_length, sr)
        return F0Result(f0_hz=np.asarray(f0s, dtype=float), times_s=times)