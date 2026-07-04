# DTW Alignment Spec

## Purpose

Provide a small, interview-ready score-to-performance alignment demo for a violin learning app. The demo should show a complete vertical slice: parse a short MusicXML score, derive reference note events, align a performed F0 contour with DTW, and export per-note feedback.

The primary score is shared with `MusicXML2MIDI`:

```text
MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml
```

The old long-form Bach prototype is intentionally not part of the tracked demo path; this spec focuses on the short shared score.

## Inputs

- Score: MusicXML or MXL parsed with `music21`.
- Tempo: explicit score tempo marks when available; otherwise `100 BPM` default.
- Performance source:
  - `synthetic`: deterministic F0 generated from the score events.
  - `f0-csv`: experimental CSV from the F0 estimator.

The DTW demo does not run an F0 estimator internally. Estimator choice happens upstream in `f0_estimation/main.py` via `--method` when generating the CSV. The F0 module currently supports `autocorr`, `pyin`, `crepe`, and `swiftf0`, with `swiftf0` as its default CLI method.

Supported F0 CSV schemas:

- `time_s,f0_hz` from `f0_estimation/main.py`
- `t,f0_hz` from simple external F0 exports

## Score Events

The score parser exports one event per note:

- `note_index`
- `note_name`
- `midi`
- `expected_hz`
- `expected_start_s`
- `expected_end_s`
- `duration_s`

For chords, the current demo uses the highest MIDI pitch. The short Twinkle fixture is monophonic, so this is mainly a guardrail.

## Algorithm

1. Parse the MusicXML score with `music21`.
2. Build a tempo map from score metronome marks, using `100 BPM` only when no explicit tempo starts the score.
3. Convert score note offsets and durations from quarter length to seconds.
4. Convert score events to a regular F0 reference grid.
5. Load or synthesize a performed F0 grid.
6. Run exact DTW over the score and performance grids.
7. Use a frame cost made from:
   - absolute pitch distance in cents
   - pitch clipping at `300 cents`
   - unvoiced/NaN penalty
   - small optional temporal cost to keep repeated notes anchored
8. Map the DTW path back to score note indices.
9. Aggregate per-note timing and pitch feedback.

## Outputs

Generated artifacts are written to `dtw/output/`, which is ignored by git:

- `alignment_notes.csv`
- `alignment_summary.json`
- `alignment_plot.png` when `--plot` is passed

## Per-Note Metrics

The per-note table contains:

- expected note fields: `note_index`, `note_name`, `midi`, `expected_hz`, expected start/end, and duration
- `aligned_start_s`
- `aligned_end_s`
- `onset_error_ms`
- `median_cents_error`
- `duration_ratio`
- `feedback_label`

Labels:

- `OK`
- `EARLY`
- `LATE`
- `SHARP`
- `FLAT`
- `MISSED`

Pitch labels use a `25 cents` threshold. Timing labels use a `50 ms` onset threshold. Pitch labels take priority over timing labels because intonation feedback is the clearer violin-learning signal in this demo.

## CLI

Primary deterministic demo:

```powershell
python dtw/align_demo.py --score MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml --mode synthetic --plot
```

Experimental F0 CSV mode:

```powershell
python f0_estimation/main.py --audio f0_estimation/data/TwinkleTwinkleLittleStar.wav --method swiftf0 --csv f0_estimation/outputs/TwinkleTwinkleLittleStar_swiftf0.csv
python dtw/align_demo.py --mode f0-csv --score MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml --f0-csv f0_estimation/outputs/TwinkleTwinkleLittleStar_swiftf0.csv --plot
```

## Limitations

- Synthetic mode demonstrates alignment mechanics, not audio robustness.
- F0 CSV mode assumes monophonic violin and does not yet estimate score latency or trim silence automatically.
- Consecutive repeated notes remain ambiguous when pitch is identical; the temporal term helps but is not a full onset model.
- The current output does not include measure, beat, bowing, fingering, or UI-specific score coordinates.
- Exact DTW is fine for this short score; longer performances should use pruning/windowing or an approximate method.

## Next Steps

1. Add silence trimming and latency estimation before F0 CSV alignment.
2. Use onset detections from the F0 pipeline to improve repeated-note boundaries.
3. Export measure/beat positions from MusicXML for score-overlay UI.
4. Add missed-note and extra-note handling beyond simple no-data detection.
5. Validate against a short rendered WAV from `MusicXML2MIDI` and a real recorded violin phrase.
