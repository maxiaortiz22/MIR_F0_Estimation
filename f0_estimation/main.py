#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from f0_estimation.AudioIO import load_audio_mono
from f0_estimation.EstimatorFactory import create_estimator
from f0_estimation.Intonation import IntonationMetrics, compute_intonation_metrics, hz_to_midi, midi_to_note_name
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


def finite_float_or_none(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def write_csv(
    path: Path,
    times_s: np.ndarray,
    f0_hz: np.ndarray,
    cents_error: np.ndarray,
    nearest_midi: np.ndarray,
    valid_mask: np.ndarray,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time_s", "f0_hz", "nearest_note", "cents_error"])
        writer.writeheader()
        for time_s, f0, cents, midi, valid in zip(times_s, f0_hz, cents_error, nearest_midi, valid_mask):
            row = {"time_s": f"{time_s:.6f}", "f0_hz": "", "nearest_note": "", "cents_error": ""}
            if valid and np.isfinite(f0):
                row["f0_hz"] = f"{float(f0):.6f}"
                row["nearest_note"] = midi_to_note_name(float(midi))
                row["cents_error"] = f"{float(cents):.6f}"
            writer.writerow(row)


def build_json_summary(
    audio_path: Path,
    y: np.ndarray,
    sr: int,
    method: str,
    frame_count: int,
    f0_summary: dict[str, float],
    intonation_metrics: IntonationMetrics | None,
    onsets: np.ndarray | None,
    phrases: list[tuple[float, float]] | None,
    onset_params: dict[str, Any] | None,
) -> dict[str, Any]:
    intonation: dict[str, Any] | None = None
    if intonation_metrics is not None:
        valid_cents = intonation_metrics.cents[intonation_metrics.valid_mask]
        abs_cents = np.abs(valid_cents)
        intonation = {
            "pct_within_25_cents": intonation_metrics.pct_within_25,
            "pct_within_50_cents": intonation_metrics.pct_within_50,
            "pct_within_100_cents": intonation_metrics.pct_within_100,
            "median_abs_cents": finite_float_or_none(float(np.median(abs_cents))) if abs_cents.size else None,
            "p95_abs_cents": finite_float_or_none(float(np.percentile(abs_cents, 95))) if abs_cents.size else None,
            "median_cents_error": finite_float_or_none(float(np.median(valid_cents))) if valid_cents.size else None,
        }

    return {
        "audio": {
            "path": str(audio_path),
            "sample_rate_hz": sr,
            "samples": int(y.size),
            "duration_s": float(y.size / sr) if sr else 0.0,
        },
        "method": method,
        "f0": {
            "frames": int(frame_count),
            "voiced_frames": int(f0_summary["voiced_frames"]),
            "voicing_rate": float(f0_summary["voiced_frames"] / frame_count) if frame_count else 0.0,
            "voicing_rate_pct": f0_summary["voicing_rate_pct"],
            "median_hz": finite_float_or_none(f0_summary["median_hz"]),
            "p05_hz": finite_float_or_none(f0_summary["p05_hz"]),
            "p95_hz": finite_float_or_none(f0_summary["p95_hz"]),
        },
        "intonation": intonation,
        "segmentation": {
            "onset_count": int(onsets.size) if onsets is not None else None,
            "phrase_count": len(phrases) if phrases is not None else None,
            "onset_params": onset_params,
            "onsets_s": [float(t) for t in onsets] if onsets is not None else None,
            "phrases_s": [{"start_s": float(start), "end_s": float(end)} for start, end in phrases]
            if phrases is not None
            else None,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def write_plot(
    path: Path,
    y: np.ndarray,
    sr: int,
    times_s: np.ndarray,
    f0_hz: np.ndarray,
    cents_error: np.ndarray,
    valid_mask: np.ndarray,
    audio_path: Path,
    method: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    audio_times = np.arange(y.size) / sr

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True, constrained_layout=True)
    fig.suptitle(f"F0 demo: {audio_path.name} ({method})")

    axes[0].plot(audio_times, y, color="#2b6cb0", linewidth=0.8)
    axes[0].set_ylabel("Amplitude")
    axes[0].set_title("Waveform")
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(times_s, f0_hz, color="#2f855a", linewidth=1.2)
    axes[1].set_ylabel("F0 (Hz)")
    axes[1].set_title("F0 contour")
    axes[1].grid(True, alpha=0.25)

    cents_for_plot = np.where(valid_mask, cents_error, np.nan)
    axes[2].axhspan(-25.0, 25.0, color="#c6f6d5", alpha=0.45, label="+/-25 cents")
    axes[2].axhline(0.0, color="#1a202c", linewidth=0.8)
    axes[2].plot(times_s, cents_for_plot, color="#c53030", linewidth=1.0)
    axes[2].set_ylabel("Cents")
    axes[2].set_xlabel("Time (s)")
    axes[2].set_title("Cents error from nearest equal-tempered note")
    axes[2].set_ylim(-55.0, 55.0)
    axes[2].grid(True, alpha=0.25)
    axes[2].legend(loc="upper right")

    fig.savefig(path, dpi=160)
    plt.close(fig)


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
    parser.add_argument("--onset-delta", type=float, default=0.6, help="Onset peak-picking threshold.")
    parser.add_argument("--onset-wait", type=int, default=30, help="Minimum onset peak distance in frames.")
    parser.add_argument("--max-frame-lines", type=int, default=40, help="Maximum frame lines printed with --print-frames.")
    parser.add_argument("--csv", type=Path, help="Write per-frame CSV with time_s, f0_hz, nearest_note, cents_error.")
    parser.add_argument("--json", type=Path, help="Write JSON summary for the demo run.")
    parser.add_argument("--plot", type=Path, help="Write PNG plot with waveform, F0 contour, and cents error.")
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

    onsets = None
    phrases = None
    onset_params = None
    if not args.skip_onsets:
        print("\n=== Onsets & Phrases ===")
        onset_params = {"hop_length": 512, "onset_delta": args.onset_delta, "onset_wait": args.onset_wait}
        seg = OnsetPhraseSegmenter(
            sr=sr,
            hop_length=onset_params["hop_length"],
            onset_delta=onset_params["onset_delta"],
            onset_wait=onset_params["onset_wait"],
        )
        onsets = seg.detect_onsets(y)
        phrases = seg.segment_phrases(y, method="silence", top_db=40.0)
        print("Onsets (s):", np.round(onsets, 3))
        print("Phrases:")
        for start_s, end_s in phrases:
            print(f"  [{start_s:.3f}, {end_s:.3f}] dur={end_s - start_s:.3f}s")

    needs_intonation = bool(args.csv or args.json or args.plot or not args.skip_intonation)
    intonation_metrics = compute_intonation_metrics(result.f0_hz) if needs_intonation else None
    if not args.skip_intonation:
        print("\n=== Reference-Free Intonation ===")
        assert intonation_metrics is not None
        print(f"within +/-25c:  {intonation_metrics.pct_within_25:5.1f}%")
        print(f"within +/-50c:  {intonation_metrics.pct_within_50:5.1f}%")
        print(f"within +/-100c: {intonation_metrics.pct_within_100:5.1f}%")

    if args.csv:
        assert intonation_metrics is not None
        write_csv(
            args.csv,
            result.times_s,
            result.f0_hz,
            intonation_metrics.cents,
            intonation_metrics.nearest_midi,
            intonation_metrics.valid_mask,
        )
        print(f"\nWrote CSV: {args.csv}")

    if args.json:
        payload = build_json_summary(
            audio_path=audio_path,
            y=y,
            sr=sr,
            method=args.method,
            frame_count=len(result.f0_hz),
            f0_summary=summary,
            intonation_metrics=intonation_metrics,
            onsets=onsets,
            phrases=phrases,
            onset_params=onset_params,
        )
        write_json(args.json, payload)
        print(f"Wrote JSON: {args.json}")

    if args.plot:
        assert intonation_metrics is not None
        write_plot(
            args.plot,
            y,
            sr,
            result.times_s,
            result.f0_hz,
            intonation_metrics.cents,
            intonation_metrics.valid_mask,
            audio_path,
            args.method,
        )
        print(f"Wrote plot: {args.plot}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
