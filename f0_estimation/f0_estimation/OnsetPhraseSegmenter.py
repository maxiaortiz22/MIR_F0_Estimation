from __future__ import annotations

from typing import List, Tuple

import numpy as np
import librosa


class OnsetPhraseSegmenter:
    """Detect onsets and segment phrases for a monophonic instrument.

    Phrase strategies:
    - "silence": use librosa.effects.split on energy; contiguous non-silent regions
    - "gaps":    use detected onsets; long gaps (> gap_s) start a new phrase
    
    Onset detection parameters:
    - delta: threshold for peak picking (higher = less sensitive). Default 0.07 is
             often too sensitive for sustained instruments like violin.
    - wait:  minimum frames between consecutive onsets.
    """

    def __init__(
        self,
        sr: int,
        hop_length: int = 512,
        onset_backtrack: bool = True,
        onset_delta: float = 0.6,
        onset_wait: int = 30,
    ):
        self.sr = sr
        self.hop_length = hop_length
        self.onset_backtrack = onset_backtrack
        self.onset_delta = onset_delta
        self.onset_wait = onset_wait

    def detect_onsets(self, y: np.ndarray) -> np.ndarray:
        """Return onset times (seconds)."""
        oenv = librosa.onset.onset_strength(y=y, sr=self.sr, hop_length=self.hop_length)
        onsets = librosa.onset.onset_detect(
            onset_envelope=oenv,
            sr=self.sr,
            hop_length=self.hop_length,
            backtrack=self.onset_backtrack,
            units="time",
            delta=self.onset_delta,
            wait=self.onset_wait,
        )
        return onsets

    def segment_phrases(
        self,
        y: np.ndarray,
        method: str = "silence",
        top_db: float = 40.0,
        gap_s: float = 0.6,
    ) -> List[Tuple[float, float]]:
        """Return list of (start_s, end_s) phrase boundaries."""
        if method == "silence":
            intervals = librosa.effects.split(y, top_db=top_db)
            return [(b / self.sr, e / self.sr) for (b, e) in intervals]
        if method == "gaps":
            onsets = self.detect_onsets(y)
            if onsets.size == 0:
                return [(0.0, len(y) / self.sr)]
            times = np.concatenate([onsets, [len(y) / self.sr]])
            phrases: List[Tuple[float, float]] = []
            start = 0.0
            for i in range(1, len(times)):
                if times[i] - times[i - 1] > gap_s:
                    phrases.append((start, times[i - 1]))
                    start = times[i - 1]
            phrases.append((start, times[-1]))
            return phrases
        raise ValueError("method must be 'silence' or 'gaps'")


