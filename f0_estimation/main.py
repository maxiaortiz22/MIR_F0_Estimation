#!/usr/bin/env python3
"""
F0 Toolkit – OOP prototype for violin (or monophonic instrument) audio.

Implements a common interface with multiple estimators:
- Autocorrelation (classic time‑domain approach)
- pYIN (librosa)
- CREPE (deep learning)
- SwiftF0 (fast DL pitch; optional dependency)

Notes:
- Output prints timestamp (s) and F0 (Hz) per analysis frame.
- pYIN needs librosa>=0.8; CREPE needs the 'crepe' package.
- SwiftF0 is optional; this wrapper tries common packages and will guide you if missing.
"""
from __future__ import annotations

import sys
from typing import Tuple, Optional

import numpy as np
import soundfile as sf
import librosa

from f0_estimation.AutocorrEstimator import AutocorrEstimator
from f0_estimation.PyYINEstimator import PyYINEstimator
from f0_estimation.CrepeEstimator import CrepeEstimator
from f0_estimation.SwiftF0Estimator import SwiftF0Estimator
from f0_estimation.BaseF0Estimator import BaseF0Estimator
from f0_estimation.OnsetPhraseSegmenter import OnsetPhraseSegmenter
from f0_estimation.Intonation import (
    compute_intonation_metrics,
    midi_to_note_name,
    hz_to_midi,
)


class EstimatorFactory:
    @staticmethod
    def create(name: str) -> BaseF0Estimator:
        key = name.lower()
        if key in {"autocorr", "autocorrelation"}:
            return AutocorrEstimator()
        if key in {"pyin", "p_yin"}:
            return PyYINEstimator()
        if key == "crepe":
            return CrepeEstimator()
        if key in {"swiftf0", "swift_f0", "swift"}:
            return SwiftF0Estimator()
        raise ValueError(f"Unknown method '{name}'. Use one of: autocorr, pyin, crepe, swiftf0")


def load_audio_mono(path: str, sr: Optional[int] = None) -> Tuple[np.ndarray, int]:
    """Load audio as mono float waveform using soundfile/librosa fallback."""
    # Prefer soundfile if available for FLAC/WAV
    if sf is not None:
        y, file_sr = sf.read(path, always_2d=False)
        if y.ndim > 1:
            y = y.mean(axis=1)
        if sr is not None and file_sr != sr:
            y = librosa.resample(y.astype(float), orig_sr=file_sr, target_sr=sr)
            final_sr = sr
        else:
            final_sr = file_sr
        y = y.astype(np.float32)
        return y, final_sr
    # Fallback to librosa loader
    y, file_sr = librosa.load(path, sr=sr, mono=True)
    return y.astype(np.float32), (sr or file_sr)


def main():
    # Variables
    AUDIO_PATH = "data/HB-1.wav"  # <- audio file path
    METHOD = "swiftf0"                     # <- 'autocorr', 'pyin', 'crepe', 'swiftf0'
    SR = None                           # <- sr number or None to respect the audio file's sr
    PRINT_UNVOICED = False              # <- True to print unvoiced frames (NaN)
    RUN_DEMO_ONSETS = True              # <- True to run the onset and phrase demo
    RUN_DEMO_INTONATION = True          # <- True to run the intonation demo

    y, sr = load_audio_mono(AUDIO_PATH, sr=SR)
    estimator = EstimatorFactory.create(METHOD)

    try:
        result = estimator.estimate(y, sr)
    except ModuleNotFoundError as e:
        print(f"ERROR: Missing dependency for {METHOD}: {e}. Please install the required package.")
        sys.exit(2)
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(2)

    # Pretty print
    print(f"Method: {METHOD}")
    print(f"Frames: {len(result.f0_hz)}, SR: {sr}")
    for t, f0 in zip(result.times_s, result.f0_hz):
        if np.isnan(f0):
            if PRINT_UNVOICED:
                print(f"t={t:8.3f}s : F0 = NaN")
            continue
        print(f"t={t:8.3f}s : F0 = {f0:8.2f} Hz")

    # Demos
    if RUN_DEMO_ONSETS:
        print("\n=== Demo 2) Onsets & Phrases ===")
        # onset_delta: higher = less sensitive (default 0.07 is too sensitive for violin)
        # onset_wait:  minimum frames between onsets (avoids close false positives)
        seg = OnsetPhraseSegmenter(
            sr=sr,
            hop_length=512,
            onset_delta=0.6,   # <- increase for sustained notes (try 0.2-0.5)
            onset_wait=30,     # <- min frames between onsets (~0.35s at sr=44100)
        )
        onsets = seg.detect_onsets(y)
        phrases = seg.segment_phrases(y, method="silence", top_db=40.0)
        print("Onsets (s):", np.round(onsets, 3))
        print("Phrases (s):")
        for (a, b) in phrases:
            print(f"  [{a:.3f}, {b:.3f}]  dur={b-a:.3f}s")

    if RUN_DEMO_INTONATION:
        print("\n=== Demo 3) Intonation (reference-free) ===")
        metrics = compute_intonation_metrics(result.f0_hz)
        print("Intonation score (reference-free):")
        print(f"  within ±25c:  {metrics.pct_within_25:5.1f}%")
        print(f"  within ±50c:  {metrics.pct_within_50:5.1f}%")
        print(f"  within ±100c: {metrics.pct_within_100:5.1f}%")
        # Filter valid (non-NaN) frames first, then take first 10
        valid_samples = [
            (t, hz, c)
            for t, hz, c in zip(result.times_s, result.f0_hz, metrics.cents)
            if not np.isnan(hz)
        ]
        for t, hz, c in valid_samples[:len(valid_samples)]: # [:10] , [:len(valid_samples)]
            note = midi_to_note_name(hz_to_midi(np.array([hz]))[0])
            print(f"t={t:7.3f}s  f0={hz:7.2f} Hz  err={c:6.1f} cents -> nearest={note}")
if __name__ == "__main__":
    main()
