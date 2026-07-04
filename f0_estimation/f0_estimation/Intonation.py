from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def hz_to_midi(f: np.ndarray) -> np.ndarray:
    f = np.asarray(f, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        midi = 69.0 + 12.0 * np.log2(f / 440.0)
    return midi


def midi_to_note_name(midi: float) -> str:
    n = int(round(midi))
    name = NOTE_NAMES[n % 12]
    octave = (n // 12) - 1
    return f"{name}{octave}"


def cents_error_from_nearest(f0_hz: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (cents_error, nearest_note_midi, mask_valid).

    cents in [-50, +50] relative to nearest equal-tempered note.
    """
    midi = hz_to_midi(f0_hz)
    nearest = np.rint(midi)
    cents = 100.0 * (midi - nearest)
    valid = np.isfinite(midi)
    return cents, nearest, valid


@dataclass
class IntonationMetrics:
    cents: np.ndarray
    nearest_midi: np.ndarray
    valid_mask: np.ndarray
    pct_within_25: float
    pct_within_50: float
    pct_within_100: float


def compute_intonation_metrics(f0_hz: np.ndarray) -> IntonationMetrics:
    cents, nearest, valid = cents_error_from_nearest(f0_hz)
    abs_cents = np.abs(cents[valid])

    def pct(threshold: float) -> float:
        return float(100.0 * np.mean(abs_cents <= threshold)) if abs_cents.size else 0.0

    return IntonationMetrics(
        cents=cents,
        nearest_midi=nearest,
        valid_mask=valid,
        pct_within_25=pct(25.0),
        pct_within_50=pct(50.0),
        pct_within_100=pct(100.0),
    )


