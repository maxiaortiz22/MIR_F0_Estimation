from .BaseF0Estimator import BaseF0Estimator, F0Result
import numpy as np
import importlib
import librosa


class CrepeEstimator(BaseF0Estimator):
    def __init__(self, step_size_ms: int = 10, model_capacity: str = "full", viterbi: bool = True):
        self.step_size_ms = step_size_ms
        self.model_capacity = model_capacity  # 'tiny', 'small', 'medium', 'large', 'full'
        self.viterbi = viterbi

    def estimate(self, y: np.ndarray, sr: int) -> F0Result:
        crepe = importlib.import_module("crepe")  # raise if missing
        # CREPE expects 16 kHz mono float32
        target_sr = 16000
        if sr != target_sr:
            y16 = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
            sr16 = target_sr
        else:
            y16 = y
            sr16 = sr
        y16 = y16.astype(np.float32)

        # crepe.predict returns: time (s), frequency (Hz), confidence, activation
        time_s, frequency_hz, confidence, activation = crepe.predict(
            y16,
            sr16,
            step_size=self.step_size_ms,
            model_capacity=self.model_capacity,
            viterbi=self.viterbi,
        )
        return F0Result(f0_hz=frequency_hz.astype(float), times_s=time_s.astype(float))