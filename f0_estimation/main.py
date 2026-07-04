#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from f0_estimation.AudioIO import load_audio_mono
from f0_estimation.EstimatorFactory import create_estimator
from f0_estimation.Intonation import compute_intonation_metrics, hz_to_midi, midi_to_note_name
from f0_estimation.OnsetPhraseSegmenter import OnsetPhraseSegmenter


DEFAULT_AUDIO = Path(__file__).resolve().parent / "data" / "A_STRING.wav"


def summarize_f0(f0_hz: np.ndarray) -> dict[str, float]:
    valid = f0_hz[np.isfinite(f0_hz)]
    if valid.size == 0:
        return {
            "voiced_frames": 0,
            "voicing_rate_pct": 0.0,
            "median_hz": float("nan"),
            "p05_hz": float("nan"),
            "p95_hz": float("nan"),
        }
    return {
        "voiced_frames": int(valid.size),
        "voicing_rate_pct": float(100.0 * valid.size / f0_hz.size),
        "median_hz": float(np.median(valid)),
        "p05_hz": float(np.percentile(valid, 5)),
        "p95_hz": float(np.percentile(valid, 95)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Estimate F0, intonation, onsets, and phrases for violin audio.")
    parser.add_argument("--audio", default=str(DEFAULT_AUDIO), help="Path to a mono/stereo WAV file.")
    parser.add_argument(
        "--method",
        default="swiftf0",
        choices=["autocorr", "pyin", "crepe", "swiftf0"],
        help="F0 estimator to use.",
    )
    parser.add_argument("--sr", type=int, default=None, help="Optional target sample rate.")
    parser.add_argument("--print-frames", action="store_true", help="Print every voiced analysis frame.")
    parser.add_argument("--print-unvoiced", action="store_true", help="Include unvoiced frames when printing frames.")
    parser.add_argument("--skip-onsets", action="store_true", help="Skip onset and phrase analysis.")
    parser.add_argument("--skip-intonation", action="store_true", help="Skip reference-free intonation metrics.")
    parser.add_argument("--max-frame-lines", type=int, default=40, help="Maximum frame lines printed with --print-frames.")
    return parser


def print_frame_table(times_s: np.ndarray, f0_hz: np.ndarray, max_lines: int, print_unvoiced: bool) -> None:
    printed = 0
    for t, f0 in zip(times_s, f0_hz):
        if not np.isfinite(f0):
            if print_unvoiced:
                print(f"t={t:8.3f}s : F0 = NaN")
                printed += 1
        else:
            note = midi_to_note_name(float(hz_to_midi(np.array([f0]))[0]))
            print(f"t={t:8.3f}s : F0 = {f0:8.2f} Hz -> {note}")
            printed += 1
        if printed >= max_lines:
            remaining = len(f0_hz) - printed
            if remaining > 0:
                print(f"... truncated after {printed} frame lines")
            break


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    audio_path = Path(args.audio)

    try:
        y, sr = load_audio_mono(audio_path, sr=args.sr)
        estimator = create_estimator(args.method)
        result = estimator.estimate(y, sr)
    except (FileNotFoundError, ModuleNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    summary = summarize_f0(result.f0_hz)
    print("=== F0 Demo ===")
    print(f"Audio: {audio_path}")
    print(f"Method: {args.method}")
    print(f"Sample rate: {sr} Hz")
    print(f"Frames: {len(result.f0_hz)}")
    print(f"Voiced frames: {summary['voiced_frames']} ({summary['voicing_rate_pct']:.1f}%)")
    print(
        "F0 median/p05/p95: "
        f"{summary['median_hz']:.2f} / {summary['p05_hz']:.2f} / {summary['p95_hz']:.2f} Hz"
    )

    if np.isfinite(summary["median_hz"]):
        median_midi = float(hz_to_midi(np.array([summary["median_hz"]]))[0])
        print(f"Median nearest note: {midi_to_note_name(median_midi)}")

    if args.print_frames:
        print("\n=== Frames ===")
        print_frame_table(result.times_s, result.f0_hz, args.max_frame_lines, args.print_unvoiced)

    if not args.skip_onsets:
        print("\n=== Onsets & Phrases ===")
        seg = OnsetPhraseSegmenter(sr=sr, hop_length=512, onset_delta=0.6, onset_wait=30)
        onsets = seg.detect_onsets(y)
        phrases = seg.segment_phrases(y, method="silence", top_db=40.0)
        print("Onsets (s):", np.round(onsets, 3))
        print("Phrases:")
        for start_s, end_s in phrases:
            print(f"  [{start_s:.3f}, {end_s:.3f}] dur={end_s - start_s:.3f}s")

    if not args.skip_intonation:
        print("\n=== Reference-Free Intonation ===")
        metrics = compute_intonation_metrics(result.f0_hz)
        print(f"within +/-25c:  {metrics.pct_within_25:5.1f}%")
        print(f"within +/-50c:  {metrics.pct_within_50:5.1f}%")
        print(f"within +/-100c: {metrics.pct_within_100:5.1f}%")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
