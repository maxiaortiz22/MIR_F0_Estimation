#!/usr/bin/env python3
"""
Score Alignment (DTW) – Standalone prototype

This project is intentionally separate from the F0 detector so you can demo them independently.

It aligns a reference score (MusicXML) to an F0 time series using DTW on cents.
You can either:
  A) Load F0 from a CSV produced by your F0 project (t,f0_hz), or
  B) Compute F0 inside this script using SwiftF0 or pYIN (optional path).

Dependencies:
  pip install music21 fastdtw numpy pandas librosa soundfile swift-f0

Usage: (edit variables in __main__)
  - Set MODE = "csv" to read F0 from CSV   (columns: t,f0_hz)
  - Set MODE = "compute" to compute F0 from audio using SwiftF0 or pYIN

Outputs:
  - Console summary: DTW path cost, per-note median cents, onset error (ms)
  - Optional CSV export per note
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np
import pandas as pd

# Optional: only needed if MODE=="compute"
try:
    import librosa
    import soundfile as sf
except Exception:
    librosa = None
    sf = None

try:
    from music21 import converter, tempo, note, chord
except Exception:
    converter = None  # fail later with friendly message

try:
    from fastdtw import fastdtw
except Exception:
    fastdtw = None

# Optional: only if METHOD=="swiftf0" in compute mode
try:
    from swift_f0 import SwiftF0
except Exception:
    SwiftF0 = None


def require_music21():
    if converter is None:
        raise RuntimeError("music21 is required. Install with: pip install music21")

def require_fastdtw():
    if fastdtw is None:
        raise RuntimeError("fastdtw is required. Install with: pip install fastdtw")

def require_librosa():
    if librosa is None:
        raise RuntimeError("librosa/soundfile required for audio I/O. pip install librosa soundfile")


# ------------------------------
# Score parsing
# ------------------------------

@dataclass
class ScoreEvent:
    start_s: float
    end_s: float
    midi: float
    name: str

class ScoreReference:
    def __init__(self, events: List[ScoreEvent]):
        self.events = events

    @staticmethod
    def midi_to_hz(midi: float, a4: float = 440.0) -> float:
        return float(a4 * (2.0 ** ((midi - 69.0) / 12.0)))

    @classmethod
    def from_musicxml(cls, xml_path: str, a4: float = 440.0) -> "ScoreReference":
        require_music21()
        s = converter.parse(xml_path)
        bpm = 120.0  # default
        sec_per_quarter = 60.0 / bpm
        t = 0.0
        events: List[ScoreEvent] = []
        flat = s.flatten()
        for el in flat:
            if isinstance(el, tempo.MetronomeMark) and el.number is not None:
                bpm = float(el.number)
                sec_per_quarter = 60.0 / bpm
            elif isinstance(el, (note.Note, chord.Chord)):
                ql = float(el.quarterLength)
                dur = ql * sec_per_quarter
                midi_val = float(el.pitch.midi if isinstance(el, note.Note) else max(p.midi for p in el.pitches))
                name = el.nameWithOctave if isinstance(el, note.Note) else el.closedPosition().root().name
                events.append(ScoreEvent(start_s=t, end_s=t + dur, midi=midi_val, name=name))
                t += dur
            elif isinstance(el, note.Rest):
                ql = float(el.quarterLength)
                dur = ql * sec_per_quarter
                t += dur
        return cls(events)

    def to_time_hz_series(self, hop_s: float = 0.01, a4: float = 440.0) -> Tuple[np.ndarray, np.ndarray]:
        if not self.events:
            return np.array([]), np.array([])
        t_end = max(ev.end_s for ev in self.events)
        times = np.arange(0.0, t_end, hop_s)
        hz = np.full_like(times, np.nan, dtype=float)
        for ev in self.events:
            mask = (times >= ev.start_s) & (times < ev.end_s)
            hz[mask] = self.midi_to_hz(ev.midi, a4=a4)
        return times, hz


# ------------------------------
# F0 series (import from CSV) or compute
# ------------------------------

class F0Series:
    @staticmethod
    def from_csv(csv_path: str) -> Tuple[np.ndarray, np.ndarray]:
        df = pd.read_csv(csv_path)
        if not {"t", "f0_hz"}.issubset(df.columns):
            raise ValueError("CSV must have columns: t,f0_hz")
        t = df["t"].to_numpy(dtype=float)
        f0 = df["f0_hz"].to_numpy(dtype=float)
        return t, f0

    @staticmethod
    def compute_from_audio(audio_path: str, method: str = "swiftf0", sr: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        require_librosa()
        y, file_sr = librosa.load(audio_path, sr=sr, mono=True)
        sr = sr or file_sr
        if method.lower() in {"swiftf0", "swift"}:
            if SwiftF0 is None:
                raise RuntimeError("pip install swift-f0 to use SwiftF0")
            det = SwiftF0(fmin=65.0, fmax=2000.0, confidence_threshold=0.9)
            res = det.detect_from_array(y.astype(np.float32), sr)
            return np.asarray(res.timestamps, float), np.asarray(res.pitch_hz, float)
        elif method.lower() == "pyin":
            f0, _, _ = librosa.pyin(y, fmin=65.0, fmax=2000.0, sr=sr)
            t = librosa.times_like(f0, sr=sr)
            return t.astype(float), f0.astype(float)
        else:
            raise ValueError("method must be 'swiftf0' or 'pyin'")


# ------------------------------
# Alignment (DTW on cents)
# ------------------------------

def cents_diff(f_hz: float, g_hz: float) -> float:
    """Cents difference; returns NaN if either side undefined or non-positive."""
    if not np.isfinite(f_hz) or not np.isfinite(g_hz) or f_hz <= 0 or g_hz <= 0:
        return float('nan')
    return 1200.0 * np.log2(f_hz / g_hz)


def resample_to_grid(times: np.ndarray, values: np.ndarray, hop_s: float) -> Tuple[np.ndarray, np.ndarray]:
    if times.size == 0:
        return np.array([]), np.array([])
    t_end = float(times[-1])
    grid = np.arange(0.0, t_end + 1e-9, hop_s)
    out = np.full_like(grid, np.nan, dtype=float)
    j = 0
    for i, t in enumerate(grid):
        while j + 1 < len(times) and times[j + 1] <= t:
            j += 1
        out[i] = values[j]
    return grid, out

@dataclass
class AlignmentResult:
    path_cost: float
    path: List[Tuple[int, int]]
    score_times: np.ndarray
    score_hz: np.ndarray
    audio_times: np.ndarray
    audio_hz: np.ndarray
    per_note_cents_median: List[float]
    per_note_onset_ms: List[float]


def run_dtw(audio_t: np.ndarray, audio_f0: np.ndarray, score_t: np.ndarray, score_hz: np.ndarray):
    require_fastdtw()
    series_a = [(float(t), float(f)) for t, f in zip(audio_t, audio_f0)]
    series_b = [(float(t), float(h)) for t, h in zip(score_t, score_hz)]

    def dist(a, b):
        _, f = a
        _, h = b
        d = cents_diff(f, h)
        if not np.isfinite(d):
            return 300.0
        return min(abs(d), 300.0)

    if not series_a or not series_b:
        raise ValueError("Empty series for DTW: check audio/score time grids")

    cost, path = fastdtw(series_a, series_b, dist=dist)
    return cost, path


def event_based_metrics(audio_t: np.ndarray,
                        audio_f0: np.ndarray,
                        score_t: np.ndarray,
                        score_hz: np.ndarray,
                        path: List[Tuple[int,int]],
                        events: List[ScoreEvent]) -> Tuple[List[float], List[float]]:
    from collections import defaultdict
    buckets = defaultdict(list)
    for ia, ib in path:
        buckets[ib].append(ia)

    # helper: map time to nearest score index
    def time_to_idx(t: float) -> int:
        if len(score_t) <= 1:
            return 0
        dt = score_t[1] - score_t[0]
        i = int(round((t - score_t[0]) / dt))
        return max(0, min(len(score_t) - 1, i))

    per_note_cents = []
    per_note_onset = []
    for ev in events:
        s0 = time_to_idx(ev.start_s)
        s1 = time_to_idx(max(ev.start_s, ev.end_s - 1e-9))
        idxs = list(range(min(s0, s1), max(s0, s1) + 1))
        audio_idxs = [ia for ib in idxs for ia in buckets.get(ib, [])]
        # cents median
        cents_vals = [cents_diff(audio_f0[ia], score_hz[ib]) for ib in idxs for ia in buckets.get(ib, [])]
        cents_vals = [c for c in cents_vals if np.isfinite(c) and abs(c) <= 300]
        med = float(np.median(cents_vals)) if cents_vals else float('nan')
        per_note_cents.append(med)
        # onset error
        if audio_idxs:
            t_score_on = score_t[min(idxs)]
            t_audio_on = float(np.min([audio_t[ia] for ia in audio_idxs]))
            per_note_onset.append(1000.0 * (t_audio_on - t_score_on))
        else:
            per_note_onset.append(float('nan'))
    return per_note_cents, per_note_onset



# ------------------------------
# __main__ – edit here (no CLI)
# ------------------------------

if __name__ == "__main__":
    # === Choose mode ===
    MODE = "compute"          # "csv" (load F0) or "compute" (compute F0 here)

    # === Paths ===
    MUSICXML_PATH = "bwv1001.mxl"
    F0_CSV_PATH   = "twinkle_f0.csv"      # used if MODE=="csv" (columns: t,f0_hz)      # used if MODE=="csv" (columns: t,f0_hz)
    AUDIO_PATH    = "emil-telmanyi_bwv1001.wav"  # used if MODE=="compute"  # used if MODE=="compute"

    # === Compute settings (if MODE=="compute") ===
    METHOD = "swiftf0"       # "swiftf0" or "pyin" or "pyin"
    SR = None                # resample rate or None

    # === Series grid ===
    HOP_S = 0.02            # 20 ms grid (más robusto)
    PREROLL_DROP_S = 0.10   # ignora primeros 100 ms de audio F0
    MATCH_SCORE_TO_AUDIO_DURATION = True  # escala el score a la duración del audio (global)
    A4_REF = 440.0

    # === Load score ===
    score = ScoreReference.from_musicxml(MUSICXML_PATH, a4=A4_REF)
    score_t, score_hz = score.to_time_hz_series(hop_s=HOP_S, a4=A4_REF)

    # === Load or compute F0 ===
    if MODE == "csv":
        audio_t, audio_f0 = F0Series.from_csv(F0_CSV_PATH)
    elif MODE == "compute":
        audio_t, audio_f0 = F0Series.compute_from_audio(AUDIO_PATH, method=METHOD, sr=SR)
    else:
        raise ValueError("MODE must be 'csv' or 'compute'")

    # Resample both to the same grid
    # Drop preroll from audio
    if audio_t.size:
        mask = audio_t >= PREROLL_DROP_S
        if mask.any():
            audio_t = audio_t[mask] - PREROLL_DROP_S
            audio_f0 = audio_f0[mask]

    audio_tg, audio_fg = resample_to_grid(audio_t, audio_f0, hop_s=HOP_S)

    # Match score total duration to audio (global scale)
    if MATCH_SCORE_TO_AUDIO_DURATION and audio_tg.size and score_t.size:
        scale = (audio_tg[-1] / score_t[-1]) if score_t[-1] > 0 else 1.0
        score_t = score_t * scale
        # scale events too
        # rebuild ScoreReference with scaled events
        scaled_events = [ScoreEvent(ev.start_s*scale, ev.end_s*scale, ev.midi, ev.name) for ev in score.events]
        score = ScoreReference(scaled_events)
        score_hz = np.interp(score_t, *ScoreReference.to_time_hz_series(score, hop_s=HOP_S, a4=A4_REF)) if False else score_hz

    # Trim to overlapping time range
    if audio_tg.size and score_t.size:
        t_end = min(audio_tg[-1], score_t[-1])
        audio_mask = audio_tg <= t_end
        score_mask = score_t <= t_end
        audio_tg, audio_fg = audio_tg[audio_mask], audio_fg[audio_mask]
        score_t, score_hz = score_t[score_mask], score_hz[score_mask]

    audio_fg = audio_fg.astype(float)
    score_hz = score_hz.astype(float)

    # Align (DTW) and compute event-based metrics
    cost, path = run_dtw(audio_tg, audio_fg, score_t, score_hz)

    per_note_cents, per_note_onset = event_based_metrics(audio_tg, audio_fg, score_t, score_hz, path, score.events)

    # Mimic previous API for prints/CSV
    class _AR:
        pass
    ar = _AR()
    ar.path_cost = float(cost)
    ar.per_note_cents_median = per_note_cents
    ar.per_note_onset_ms = per_note_onset
    ar.score_times = score_t
    ar.score_hz = score_hz
    ar.audio_times = audio_tg
    ar.audio_hz = audio_fg
    ar.events = score.events

    # Align
    # (computed above) ar = _AR with event-based metrics

    # Summaries
    print(f"Path cost: {ar.path_cost:.2f}")
    cents_vals = [c for c in ar.per_note_cents_median if np.isfinite(c)]
    if cents_vals:
        print(f"Per-note median |cents|: {np.median(np.abs(cents_vals)):.1f}c")
        within25 = 100.0 * np.mean(np.abs(cents_vals) <= 25)
        within50 = 100.0 * np.mean(np.abs(cents_vals) <= 50)
        print(f"Per-note within ±25c: {within25:.1f}% | ±50c: {within50:.1f}%")

    print("First notes:")
    from itertools import islice
    for i, (ev, c_med, onset_ms) in enumerate(islice(zip(ar.events, ar.per_note_cents_median, ar.per_note_onset_ms), 10)):
        ctxt = f"{c_med:6.1f}c" if np.isfinite(c_med) else "   n/a"
        print(f"note[{i:02d}] {ev.name:<4} midi={ev.midi:5.1f}  cents_med={ctxt}   onset_err={onset_ms:7.1f} ms")

    # Optional export
    EXPORT_PER_NOTE_CSV = True
    OUT_CSV = "alignment_per_note.csv"
    if EXPORT_PER_NOTE_CSV:
        rows = []
        for idx, (ev, c_med, onset_ms) in enumerate(zip(ar.events, ar.per_note_cents_median, ar.per_note_onset_ms)):
            rows.append({
                "note_index": idx,
                "note_name": ev.name,
                "note_midi": ev.midi,
                "score_start_s": float(ev.start_s),
                "score_end_s": float(ev.end_s),
                "cents_median": float(c_med) if np.isfinite(c_med) else np.nan,
                "onset_error_ms": float(onset_ms),
            })
        pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
        print(f"Saved per-note CSV -> {OUT_CSV}")
        print(f"Saved per-note CSV -> {OUT_CSV}")
