#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    from music21 import chord, converter, note, tempo
except Exception:  # pragma: no cover - handled by CliError at runtime.
    chord = None
    converter = None
    note = None
    tempo = None


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = REPO_ROOT / "MusicXML2MIDI" / "musicxml" / "DemoTwinkleShort.musicxml"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "output"
DEFAULT_HOP_S = 0.02
DEFAULT_TEMPO_BPM = 100.0
PITCH_CLIP_CENTS = 300.0
UNVOICED_PENALTY = 320.0
ONSET_THRESHOLD_MS = 50.0
PITCH_THRESHOLD_CENTS = 25.0


class CliError(ValueError):
    """Error caused by invalid user input or local setup."""


@dataclass(frozen=True)
class ScoreEvent:
    note_index: int
    note_name: str
    midi: int
    expected_hz: float
    expected_start_s: float
    expected_end_s: float
    duration_s: float


@dataclass(frozen=True)
class PerformanceEvent:
    note_index: int
    performed_start_s: float
    performed_end_s: float
    performed_hz: float
    cents_offset: float


@dataclass(frozen=True)
class NoteMetric:
    note_index: int
    note_name: str
    midi: int
    expected_hz: float
    expected_start_s: float
    expected_end_s: float
    duration_s: float
    aligned_start_s: float | None
    aligned_end_s: float | None
    onset_error_ms: float | None
    median_cents_error: float | None
    duration_ratio: float | None
    feedback_label: str


def require_music21() -> None:
    if converter is None:
        raise CliError("music21 is required. Install the project environment or run: pip install music21")


def midi_to_hz(midi: float, a4_hz: float = 440.0) -> float:
    return float(a4_hz * (2.0 ** ((float(midi) - 69.0) / 12.0)))


def hz_to_cents(performed_hz: float, expected_hz: float) -> float:
    if (
        not math.isfinite(performed_hz)
        or not math.isfinite(expected_hz)
        or performed_hz <= 0.0
        or expected_hz <= 0.0
    ):
        return float("nan")
    return float(1200.0 * math.log2(performed_hz / expected_hz))


def finite_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return float(value) if math.isfinite(float(value)) else None


def note_name_for_element(element: Any) -> str:
    if isinstance(element, note.Note):
        return str(element.nameWithOctave)
    if isinstance(element, chord.Chord):
        root = element.root()
        return str(root.nameWithOctave if root is not None else element.pitches[0].nameWithOctave)
    return "unknown"


def midi_for_element(element: Any) -> int:
    if isinstance(element, note.Note):
        return int(element.pitch.midi)
    if isinstance(element, chord.Chord):
        return int(max(pitch.midi for pitch in element.pitches))
    raise TypeError(f"unsupported score element: {type(element)!r}")


def extract_tempo_marks(score: Any, default_bpm: float) -> list[tuple[float, float]]:
    marks: list[tuple[float, float]] = []
    for mark in score.recurse().getElementsByClass(tempo.MetronomeMark):
        if mark.number is None:
            continue
        offset = float(mark.getOffsetInHierarchy(score))
        marks.append((offset, float(mark.number)))

    marks.sort(key=lambda item: item[0])
    if not marks or marks[0][0] > 0.0:
        marks.insert(0, (0.0, default_bpm))
    return marks


def quarter_to_seconds(quarter_offset: float, tempo_marks: list[tuple[float, float]]) -> float:
    elapsed = 0.0
    for index, (start_ql, bpm) in enumerate(tempo_marks):
        next_ql = tempo_marks[index + 1][0] if index + 1 < len(tempo_marks) else None
        if quarter_offset <= start_ql:
            break
        segment_end = quarter_offset if next_ql is None else min(quarter_offset, next_ql)
        if segment_end > start_ql:
            elapsed += (segment_end - start_ql) * (60.0 / bpm)
        if next_ql is None or quarter_offset < next_ql:
            break
    return float(elapsed)


def parse_score_events(score_path: Path, default_bpm: float = DEFAULT_TEMPO_BPM) -> tuple[list[ScoreEvent], list[tuple[float, float]]]:
    require_music21()
    if not score_path.exists():
        raise CliError(f"score not found: {score_path}")

    try:
        score = converter.parse(str(score_path))
    except Exception as exc:
        raise CliError(f"could not parse score '{score_path}': {exc}") from exc

    tempo_marks = extract_tempo_marks(score, default_bpm=default_bpm)
    score_elements = []
    for element in score.recurse().notesAndRests:
        if isinstance(element, (note.Note, chord.Chord)):
            score_elements.append(element)

    events: list[ScoreEvent] = []
    for index, element in enumerate(score_elements):
        start_ql = float(element.getOffsetInHierarchy(score))
        end_ql = start_ql + float(element.duration.quarterLength)
        start_s = quarter_to_seconds(start_ql, tempo_marks)
        end_s = quarter_to_seconds(end_ql, tempo_marks)
        midi = midi_for_element(element)
        events.append(
            ScoreEvent(
                note_index=index,
                note_name=note_name_for_element(element),
                midi=midi,
                expected_hz=midi_to_hz(midi),
                expected_start_s=start_s,
                expected_end_s=end_s,
                duration_s=end_s - start_s,
            )
        )

    if not events:
        raise CliError(f"score has no note events: {score_path}")
    return events, tempo_marks


def events_to_series(events: list[ScoreEvent], hop_s: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    end_s = max(event.expected_end_s for event in events)
    times = np.arange(0.0, end_s + hop_s * 0.5, hop_s, dtype=float)
    hz = np.full(times.shape, np.nan, dtype=float)
    note_indices = np.full(times.shape, -1, dtype=int)

    for event in events:
        mask = (times >= event.expected_start_s) & (times < event.expected_end_s)
        if event.note_index == events[-1].note_index:
            mask = (times >= event.expected_start_s) & (times <= event.expected_end_s)
        hz[mask] = event.expected_hz
        note_indices[mask] = event.note_index
    return times, hz, note_indices


def cents_to_hz(expected_hz: float, cents: float) -> float:
    return float(expected_hz * (2.0 ** (cents / 1200.0)))


def build_synthetic_performance(events: list[ScoreEvent], hop_s: float) -> tuple[np.ndarray, np.ndarray, list[PerformanceEvent]]:
    onset_offsets_s = [0.00, -0.04, 0.03, 0.07, -0.02, 0.01, 0.06, -0.01, 0.02, -0.05, 0.04, 0.06, -0.03, 0.01]
    duration_scales = [1.00, 0.95, 1.05, 0.92, 1.02, 1.08, 0.96, 1.00, 0.94, 1.04, 1.02, 0.95, 1.05, 1.00]
    cents_offsets = [4.0, -7.0, 16.0, 31.0, -34.0, 8.0, 0.0, -12.0, 22.0, -29.0, 6.0, 15.0, -10.0, 3.0]

    perf_events: list[PerformanceEvent] = []
    for event in events:
        i = event.note_index % len(onset_offsets_s)
        start_s = max(0.0, event.expected_start_s + onset_offsets_s[i])
        duration_s = max(hop_s * 2.0, event.duration_s * duration_scales[i])
        end_s = start_s + duration_s
        cents_offset = cents_offsets[i]
        perf_events.append(
            PerformanceEvent(
                note_index=event.note_index,
                performed_start_s=start_s,
                performed_end_s=end_s,
                performed_hz=cents_to_hz(event.expected_hz, cents_offset),
                cents_offset=cents_offset,
            )
        )

    end_s = max(event.performed_end_s for event in perf_events)
    times = np.arange(0.0, end_s + hop_s * 0.5, hop_s, dtype=float)
    f0 = np.full(times.shape, np.nan, dtype=float)

    for perf_event in perf_events:
        mask = (times >= perf_event.performed_start_s) & (times < perf_event.performed_end_s)
        f0[mask] = perf_event.performed_hz

    # Add a few deterministic unvoiced frames so the demo exercises NaN handling.
    if f0.size:
        f0[::37] = np.nan
    return times, f0, perf_events


def read_f0_csv(csv_path: Path) -> tuple[np.ndarray, np.ndarray]:
    if not csv_path.exists():
        raise CliError(f"F0 CSV not found: {csv_path}")

    times: list[float] = []
    f0_values: list[float] = []
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        time_column = "time_s" if "time_s" in columns else "t" if "t" in columns else None
        if time_column is None or "f0_hz" not in columns:
            raise CliError("F0 CSV must contain columns time_s,f0_hz or t,f0_hz")

        for row in reader:
            raw_time = (row.get(time_column) or "").strip()
            raw_f0 = (row.get("f0_hz") or "").strip()
            if not raw_time:
                continue
            times.append(float(raw_time))
            f0_values.append(float(raw_f0) if raw_f0 else float("nan"))

    if not times:
        raise CliError(f"F0 CSV has no frames: {csv_path}")
    return np.asarray(times, dtype=float), np.asarray(f0_values, dtype=float)


def resample_previous(times: np.ndarray, values: np.ndarray, hop_s: float) -> tuple[np.ndarray, np.ndarray]:
    start_s = float(times[0])
    end_s = float(times[-1])
    grid = np.arange(start_s, end_s + hop_s * 0.5, hop_s, dtype=float)
    positions = np.searchsorted(times, grid, side="right") - 1
    positions = np.clip(positions, 0, len(values) - 1)
    return grid - start_s, values[positions].astype(float)


def pitch_cost_cents(performed_hz: float, expected_hz: float) -> float:
    cents = hz_to_cents(performed_hz, expected_hz)
    if not math.isfinite(cents):
        return UNVOICED_PENALTY
    return min(abs(cents), PITCH_CLIP_CENTS)


def dtw_distance(
    perf_time: float,
    perf_hz: float,
    score_time: float,
    score_hz: float,
    time_weight: float,
) -> float:
    pitch_cost = pitch_cost_cents(perf_hz, score_hz)
    time_cost = min(abs(perf_time - score_time) * 1000.0 * time_weight, 120.0)
    return float(pitch_cost + time_cost)


def run_dtw(
    performance_times: np.ndarray,
    performance_hz: np.ndarray,
    score_times: np.ndarray,
    score_hz: np.ndarray,
    time_weight: float,
) -> tuple[float, list[tuple[int, int]]]:
    if performance_times.size == 0 or score_times.size == 0:
        raise CliError("empty time series; cannot run DTW")

    n = int(performance_times.size)
    m = int(score_times.size)
    costs = np.full((n + 1, m + 1), np.inf, dtype=float)
    costs[0, 0] = 0.0

    for i in range(1, n + 1):
        perf_time = float(performance_times[i - 1])
        perf_hz = float(performance_hz[i - 1])
        for j in range(1, m + 1):
            step_cost = dtw_distance(
                perf_time,
                perf_hz,
                float(score_times[j - 1]),
                float(score_hz[j - 1]),
                time_weight,
            )
            costs[i, j] = step_cost + min(costs[i - 1, j], costs[i, j - 1], costs[i - 1, j - 1])

    path: list[tuple[int, int]] = []
    i = n
    j = m
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        candidates = (costs[i - 1, j - 1], costs[i - 1, j], costs[i, j - 1])
        move = int(np.argmin(candidates))
        if move == 0:
            i -= 1
            j -= 1
        elif move == 1:
            i -= 1
        else:
            j -= 1

    path.reverse()
    return float(costs[n, m]), path


def choose_label(onset_error_ms: float | None, median_cents_error: float | None) -> str:
    if onset_error_ms is None and median_cents_error is None:
        return "MISSED"
    if median_cents_error is not None and median_cents_error >= PITCH_THRESHOLD_CENTS:
        return "SHARP"
    if median_cents_error is not None and median_cents_error <= -PITCH_THRESHOLD_CENTS:
        return "FLAT"
    if onset_error_ms is not None and onset_error_ms >= ONSET_THRESHOLD_MS:
        return "LATE"
    if onset_error_ms is not None and onset_error_ms <= -ONSET_THRESHOLD_MS:
        return "EARLY"
    return "OK"


def compute_note_metrics(
    events: list[ScoreEvent],
    score_note_indices: np.ndarray,
    score_hz: np.ndarray,
    performance_times: np.ndarray,
    performance_hz: np.ndarray,
    path: list[tuple[int, int]],
    hop_s: float,
) -> list[NoteMetric]:
    mapped_by_note: dict[int, list[int]] = {event.note_index: [] for event in events}
    cents_by_note: dict[int, list[float]] = {event.note_index: [] for event in events}

    for perf_i, score_j in path:
        if score_j < 0 or score_j >= score_note_indices.size:
            continue
        note_index = int(score_note_indices[score_j])
        if note_index < 0:
            continue
        mapped_by_note[note_index].append(perf_i)
        cents = hz_to_cents(float(performance_hz[perf_i]), float(score_hz[score_j]))
        if math.isfinite(cents):
            cents_by_note[note_index].append(float(np.clip(cents, -PITCH_CLIP_CENTS, PITCH_CLIP_CENTS)))

    metrics: list[NoteMetric] = []
    for event in events:
        perf_indices = sorted(set(mapped_by_note[event.note_index]))
        if perf_indices:
            aligned_start_s = float(performance_times[min(perf_indices)])
            aligned_end_s = float(performance_times[max(perf_indices)])
            onset_error_ms = 1000.0 * (aligned_start_s - event.expected_start_s)
            aligned_duration_s = max(0.0, aligned_end_s - aligned_start_s + hop_s)
            duration_ratio = aligned_duration_s / event.duration_s if event.duration_s > 0 else None
        else:
            aligned_start_s = None
            aligned_end_s = None
            onset_error_ms = None
            duration_ratio = None

        cents_values = cents_by_note[event.note_index]
        median_cents_error = float(np.median(cents_values)) if cents_values else None
        label = choose_label(onset_error_ms, median_cents_error)
        metrics.append(
            NoteMetric(
                note_index=event.note_index,
                note_name=event.note_name,
                midi=event.midi,
                expected_hz=event.expected_hz,
                expected_start_s=event.expected_start_s,
                expected_end_s=event.expected_end_s,
                duration_s=event.duration_s,
                aligned_start_s=aligned_start_s,
                aligned_end_s=aligned_end_s,
                onset_error_ms=onset_error_ms,
                median_cents_error=median_cents_error,
                duration_ratio=duration_ratio,
                feedback_label=label,
            )
        )
    return metrics


def metric_to_row(metric: NoteMetric) -> dict[str, Any]:
    return {
        "note_index": metric.note_index,
        "note_name": metric.note_name,
        "midi": metric.midi,
        "expected_hz": metric.expected_hz,
        "expected_start_s": metric.expected_start_s,
        "expected_end_s": metric.expected_end_s,
        "duration_s": metric.duration_s,
        "aligned_start_s": metric.aligned_start_s,
        "aligned_end_s": metric.aligned_end_s,
        "onset_error_ms": metric.onset_error_ms,
        "median_cents_error": metric.median_cents_error,
        "duration_ratio": metric.duration_ratio,
        "feedback_label": metric.feedback_label,
    }


def write_note_csv(path: Path, metrics: list[NoteMetric]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(metric_to_row(metrics[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for metric in metrics:
            row = metric_to_row(metric)
            writer.writerow(
                {
                    key: "" if value is None else f"{value:.6f}" if isinstance(value, float) else value
                    for key, value in row.items()
                }
            )


def write_summary_json(
    path: Path,
    mode: str,
    score_path: Path,
    tempo_marks: list[tuple[float, float]],
    events: list[ScoreEvent],
    metrics: list[NoteMetric],
    path_cost: float,
    output_paths: dict[str, Path],
    f0_csv_path: Path | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    finite_onsets = [abs(metric.onset_error_ms) for metric in metrics if metric.onset_error_ms is not None]
    finite_cents = [abs(metric.median_cents_error) for metric in metrics if metric.median_cents_error is not None]
    label_counts: dict[str, int] = {}
    for metric in metrics:
        label_counts[metric.feedback_label] = label_counts.get(metric.feedback_label, 0) + 1

    payload = {
        "mode": mode,
        "score": {
            "path": str(score_path),
            "note_count": len(events),
            "duration_s": max(event.expected_end_s for event in events),
            "tempo_marks": [{"quarter_offset": offset, "bpm": bpm} for offset, bpm in tempo_marks],
        },
        "f0_csv": str(f0_csv_path) if f0_csv_path is not None else None,
        "alignment": {
            "dtw_path_cost": path_cost,
            "median_abs_onset_error_ms": float(np.median(finite_onsets)) if finite_onsets else None,
            "median_abs_cents_error": float(np.median(finite_cents)) if finite_cents else None,
            "label_counts": label_counts,
        },
        "outputs": {name: str(output_path) for name, output_path in output_paths.items()},
        "notes": [metric_to_row(metric) for metric in metrics],
    }

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def write_alignment_plot(
    path: Path,
    score_times: np.ndarray,
    score_hz: np.ndarray,
    performance_times: np.ndarray,
    performance_hz: np.ndarray,
    metrics: list[NoteMetric],
    mode: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, constrained_layout=True)
    fig.suptitle(f"DTW score-to-performance alignment ({mode})")

    axes[0].plot(score_times, score_hz, color="#1f4e79", linewidth=1.8, label="Score reference")
    axes[0].plot(performance_times, performance_hz, color="#b23a48", linewidth=1.2, alpha=0.9, label="Performance F0")
    for metric in metrics:
        axes[0].axvline(metric.expected_start_s, color="#718096", linewidth=0.5, alpha=0.35)
    axes[0].set_ylabel("F0 (Hz)")
    axes[0].set_title("Pitch contour")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(loc="upper right")

    x = [metric.note_index for metric in metrics]
    y = [metric.median_cents_error if metric.median_cents_error is not None else np.nan for metric in metrics]
    colors = [
        "#2f855a"
        if metric.feedback_label == "OK"
        else "#d69e2e"
        if metric.feedback_label in {"EARLY", "LATE"}
        else "#c53030"
        for metric in metrics
    ]
    axes[1].axhspan(-PITCH_THRESHOLD_CENTS, PITCH_THRESHOLD_CENTS, color="#c6f6d5", alpha=0.45)
    axes[1].axhline(0.0, color="#1a202c", linewidth=0.8)
    axes[1].bar(x, y, color=colors)
    axes[1].set_ylabel("Median cents")
    axes[1].set_xlabel("Score note index")
    axes[1].set_title("Per-note pitch feedback")
    axes[1].set_ylim(-60.0, 60.0)
    axes[1].grid(True, axis="y", alpha=0.25)

    fig.savefig(path, dpi=160)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Small DTW demo: MusicXML score events -> performance F0 -> per-note violin feedback."
    )
    parser.add_argument("--score", type=Path, default=DEFAULT_SCORE, help=f"MusicXML/MXL score. Default: {DEFAULT_SCORE}")
    parser.add_argument("--mode", choices=["synthetic", "f0-csv"], default="synthetic", help="Performance source.")
    parser.add_argument("--f0-csv", type=Path, help="F0 CSV for --mode f0-csv. Supports time_s,f0_hz or t,f0_hz.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help=f"Output directory. Default: {DEFAULT_OUTPUT_DIR}")
    parser.add_argument("--hop-s", type=float, default=DEFAULT_HOP_S, help="Analysis grid hop in seconds. Default: 0.02")
    parser.add_argument("--default-tempo-bpm", type=float, default=DEFAULT_TEMPO_BPM, help="Used only if the score has no tempo mark.")
    parser.add_argument("--time-weight", type=float, default=0.12, help="Small temporal cost in cents per millisecond.")
    parser.add_argument("--plot", action="store_true", help="Write dtw/output/alignment_plot.png.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    score_path = args.score.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    f0_csv_path = args.f0_csv.expanduser().resolve() if args.f0_csv else None

    if args.hop_s <= 0.0:
        print("ERROR: --hop-s must be greater than 0", file=sys.stderr)
        return 2
    if args.default_tempo_bpm <= 0.0:
        print("ERROR: --default-tempo-bpm must be greater than 0", file=sys.stderr)
        return 2

    try:
        events, tempo_marks = parse_score_events(score_path, default_bpm=args.default_tempo_bpm)
        score_times, score_hz, score_note_indices = events_to_series(events, hop_s=args.hop_s)

        if args.mode == "synthetic":
            performance_times, performance_hz, _ = build_synthetic_performance(events, hop_s=args.hop_s)
        else:
            if f0_csv_path is None:
                raise CliError("--f0-csv is required when --mode f0-csv")
            raw_times, raw_f0 = read_f0_csv(f0_csv_path)
            performance_times, performance_hz = resample_previous(raw_times, raw_f0, hop_s=args.hop_s)

        path_cost, alignment_path = run_dtw(
            performance_times,
            performance_hz,
            score_times,
            score_hz,
            time_weight=args.time_weight,
        )
        metrics = compute_note_metrics(
            events,
            score_note_indices,
            score_hz,
            performance_times,
            performance_hz,
            alignment_path,
            hop_s=args.hop_s,
        )

        csv_path = output_dir / "alignment_notes.csv"
        json_path = output_dir / "alignment_summary.json"
        plot_path = output_dir / "alignment_plot.png"

        write_note_csv(csv_path, metrics)
        output_paths = {"csv": csv_path, "json": json_path}
        if args.plot:
            write_alignment_plot(plot_path, score_times, score_hz, performance_times, performance_hz, metrics, args.mode)
            output_paths["plot"] = plot_path

        write_summary_json(
            json_path,
            mode=args.mode,
            score_path=score_path,
            tempo_marks=tempo_marks,
            events=events,
            metrics=metrics,
            path_cost=path_cost,
            output_paths=output_paths,
            f0_csv_path=f0_csv_path,
        )

        print("=== DTW Alignment Demo ===")
        print(f"Mode: {args.mode}")
        print(f"Score: {score_path}")
        print(f"Notes: {len(events)} | score duration: {max(event.expected_end_s for event in events):.2f}s")
        print("Tempo marks: " + ", ".join(f"{bpm:g} BPM @ ql={offset:g}" for offset, bpm in tempo_marks))
        print(f"DTW path cost: {path_cost:.2f}")
        for metric in metrics:
            cents_text = "n/a" if metric.median_cents_error is None else f"{metric.median_cents_error:+.1f}c"
            onset_text = "n/a" if metric.onset_error_ms is None else f"{metric.onset_error_ms:+.0f}ms"
            print(f"{metric.note_index:02d} {metric.note_name:<3} onset={onset_text:>7} pitch={cents_text:>7} label={metric.feedback_label}")
        print(f"Wrote CSV:  {csv_path}")
        print(f"Wrote JSON: {json_path}")
        if args.plot:
            print(f"Wrote plot: {plot_path}")
        return 0
    except CliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
