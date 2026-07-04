#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from f0_estimation.AudioIO import load_audio_mono  # noqa: E402
from f0_estimation.EstimatorFactory import create_estimator  # noqa: E402


@dataclass(frozen=True)
class OpenStringCase:
    filename: str
    note: str
    expected_hz: float


OPEN_STRING_CASES = [
    OpenStringCase("A_STRING.wav", "A4", 440.0),
    OpenStringCase("E_STRING.wav", "E5", 659.2551138257398),
]


def cents_error(f0_hz: float, reference_hz: float) -> float:
    return float(1200.0 * np.log2(f0_hz / reference_hz))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test F0 estimators on violin open-string recordings.")
    parser.add_argument("--method", default="swiftf0", choices=["autocorr", "pyin", "crepe", "swiftf0"])
    parser.add_argument("--data-dir", default=str(PACKAGE_ROOT / "data"))
    parser.add_argument("--tolerance-cents", type=float, default=50.0)
    parser.add_argument("--min-voicing-rate", type=float, default=0.20)
    parser.add_argument("--trim-edge-s", type=float, default=0.50, help="Ignore attack/release edges before scoring.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data_dir = Path(args.data_dir)
    estimator = create_estimator(args.method)

    print("=== Open String F0 Check ===")
    print(f"Method: {args.method}")
    print(f"Data dir: {data_dir}")
    print()
    print("file          note  expected_hz  median_hz  cents_err  voiced_rate  result")

    failures = 0
    for case in OPEN_STRING_CASES:
        audio_path = data_dir / case.filename
        y, sr = load_audio_mono(audio_path)
        result = estimator.estimate(y, sr)

        keep = np.isfinite(result.f0_hz)
        keep &= result.times_s >= args.trim_edge_s
        if result.times_s.size:
            keep &= result.times_s <= (float(result.times_s[-1]) - args.trim_edge_s)

        valid_f0 = result.f0_hz[keep]
        voicing_rate = float(valid_f0.size / result.f0_hz.size) if result.f0_hz.size else 0.0
        if valid_f0.size == 0:
            median_hz = float("nan")
            cents = float("nan")
        else:
            median_hz = float(np.median(valid_f0))
            cents = cents_error(median_hz, case.expected_hz)

        passed = (
            np.isfinite(cents)
            and abs(cents) <= args.tolerance_cents
            and voicing_rate >= args.min_voicing_rate
        )
        failures += 0 if passed else 1
        print(
            f"{case.filename:<13} {case.note:<4} "
            f"{case.expected_hz:11.2f} {median_hz:10.2f} {cents:10.1f} "
            f"{100.0 * voicing_rate:10.1f}%  {'PASS' if passed else 'FAIL'}"
        )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
