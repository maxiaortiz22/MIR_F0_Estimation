#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from f0_estimation.AudioIO import load_audio_mono  # noqa: E402
from f0_estimation.EstimatorFactory import create_estimator  # noqa: E402
from f0_estimation.Intonation import compute_intonation_metrics, midi_to_note_name  # noqa: E402
from f0_estimation.OnsetPhraseSegmenter import OnsetPhraseSegmenter  # noqa: E402


DEFAULT_AUDIO = PACKAGE_ROOT / "data" / "TwinkleTwinkleLittleStar.wav"
EXPECTED_NOTES = {"C5", "D5", "E5", "G5", "A5"}


def cents_span(low_hz: float, high_hz: float) -> float:
    return float(1200.0 * np.log2(high_hz / low_hz))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test the Twinkle Twinkle melodic F0 demo clip.")
    parser.add_argument("--audio", default=str(DEFAULT_AUDIO), help="Path to the Twinkle demo WAV file.")
    parser.add_argument("--method", default="swiftf0", choices=["autocorr", "pyin", "crepe", "swiftf0"])
    parser.add_argument("--min-voicing-rate", type=float, default=0.55)
    parser.add_argument("--min-distinct-notes", type=int, default=5)
    parser.add_argument("--min-onset-count", type=int, default=12)
    parser.add_argument("--min-pitch-span-cents", type=float, default=500.0)
    parser.add_argument("--min-within-50c", type=float, default=95.0)
    parser.add_argument("--onset-delta", type=float, default=0.12)
    parser.add_argument("--onset-wait", type=int, default=25)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    audio_path = Path(args.audio)
    y, sr = load_audio_mono(audio_path)
    result = create_estimator(args.method).estimate(y, sr)
    metrics = compute_intonation_metrics(result.f0_hz)

    valid_f0 = result.f0_hz[np.isfinite(result.f0_hz)]
    voicing_rate = float(valid_f0.size / result.f0_hz.size) if result.f0_hz.size else 0.0
    if valid_f0.size:
        p05_hz, p95_hz = np.percentile(valid_f0, [5, 95])
        span_cents = cents_span(float(p05_hz), float(p95_hz))
    else:
        p05_hz = p95_hz = span_cents = float("nan")

    notes = {
        midi_to_note_name(float(midi))
        for midi in metrics.nearest_midi[metrics.valid_mask]
        if np.isfinite(midi)
    }
    missing_notes = sorted(EXPECTED_NOTES - notes)
    seg = OnsetPhraseSegmenter(sr=sr, hop_length=512, onset_delta=args.onset_delta, onset_wait=args.onset_wait)
    onsets = seg.detect_onsets(y)
    phrases = seg.segment_phrases(y, method="silence", top_db=40.0)

    checks = {
        "voicing_rate": voicing_rate >= args.min_voicing_rate,
        "distinct_notes": len(notes) >= args.min_distinct_notes,
        "onset_count": len(onsets) >= args.min_onset_count,
        "phrase_count": len(phrases) == 1,
        "expected_notes": not missing_notes,
        "pitch_span": np.isfinite(span_cents) and span_cents >= args.min_pitch_span_cents,
        "intonation_within_50c": metrics.pct_within_50 >= args.min_within_50c,
    }

    print("=== Twinkle F0 Demo Check ===")
    print(f"Audio: {audio_path}")
    print(f"Method: {args.method}")
    print(f"Duration: {len(y) / sr:.3f}s @ {sr} Hz")
    print(f"Frames: {len(result.f0_hz)}")
    print(f"Voicing rate: {100.0 * voicing_rate:.1f}%")
    print(f"F0 p05/p95: {float(p05_hz):.2f} / {float(p95_hz):.2f} Hz")
    print(f"Pitch span: {span_cents:.1f} cents")
    print(f"Nearest notes: {', '.join(sorted(notes))}")
    print(f"Onsets: {len(onsets)} ({np.array2string(np.round(onsets, 3), separator=', ')})")
    print(f"Phrases: {len(phrases)}")
    print(f"within +/-50c: {metrics.pct_within_50:.1f}%")
    print()

    for name, passed in checks.items():
        print(f"{name:<22} {'PASS' if passed else 'FAIL'}")
    if missing_notes:
        print(f"Missing expected notes: {', '.join(missing_notes)}")

    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
