from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import librosa
import numpy as np
import soundfile as sf


def load_audio_mono(path: str | Path, sr: Optional[int] = None) -> Tuple[np.ndarray, int]:
    """Load an audio file as mono float32.

    Stereo files are downmixed by averaging channels. If ``sr`` is provided, the
    waveform is resampled; otherwise the original file sample rate is preserved.
    """
    audio_path = Path(path)
    y, file_sr = sf.read(audio_path, always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)

    if sr is not None and file_sr != sr:
        y = librosa.resample(y.astype(float), orig_sr=file_sr, target_sr=sr)
        return y.astype(np.float32), int(sr)

    return y.astype(np.float32), int(file_sr)
