# F0 Pipeline Spec

## Purpose

Estimate violin F0 and derive beginner-friendly intonation and segmentation metrics from short monophonic recordings.

## Inputs

- Audio file: WAV preferred.
- Sample rate: preserve source sample rate by default.
- Channels: stereo is downmixed to mono.
- Estimator: `autocorr`, `pyin`, `crepe`, or `swiftf0`.

Current tracked violin validation clips:

- `f0_estimation/data/A_STRING.wav`: open A string, A4, 440.00 Hz.
- `f0_estimation/data/E_STRING.wav`: open E string, E5, 659.26 Hz.
- `f0_estimation/data/TwinkleTwinkleLittleStar.wav`: short rendered violin melody for a non-open-string demo.

## Outputs

Current outputs:

- Per-frame timestamp in seconds.
- Per-frame F0 in Hz.
- CSV export with `time_s`, `f0_hz`, `nearest_note`, `cents_error`.
- JSON export with audio metadata, estimator, voicing rate, F0 percentiles, intonation metrics, onset count, and phrase count.
- Optional PNG plot with waveform, F0 contour, and cents error.
- Compact median/p05/p95 F0 summary.
- Reference-free intonation percentages within +/-25, +/-50, and +/-100 cents.
- Nearest equal-tempered note labels.
- Onset times.
- Phrase boundaries.

## Estimator Contract

Every estimator implements:

```python
estimate(y: np.ndarray, sr: int) -> F0Result
```

`F0Result` contains:

- `f0_hz`: one value per frame, with `NaN` for unvoiced or unknown frames.
- `times_s`: frame timestamps in seconds.

## Intonation Logic

The current intonation metric is reference-free:

1. Convert F0 Hz to MIDI pitch.
2. Round to the nearest equal-tempered MIDI note.
3. Compute cents error relative to that nearest note.
4. Report percentages of voiced frames within fixed thresholds.

This is useful for stable-note exercises and open-string demonstrations. It is not a substitute for score-aware intonation because the intended note is inferred from the performance itself.

## Onset And Phrase Logic

Onsets use librosa onset strength and peak picking. Phrase segmentation currently supports:

- `silence`: split non-silent intervals using energy.
- `gaps`: use long gaps between detected onsets.

Violin attacks can be smooth, so onset parameters must be less sensitive than a generic percussive setting.

## Validation

Current smoke test:

```powershell
conda activate musicdsp
python f0_estimation/main.py --method swiftf0 --csv f0_estimation/outputs/A_STRING_swiftf0.csv --json f0_estimation/outputs/A_STRING_swiftf0.json --plot f0_estimation/outputs/A_STRING_swiftf0.png
python f0_estimation/main.py --audio f0_estimation/data/E_STRING.wav --method swiftf0 --csv f0_estimation/outputs/E_STRING_swiftf0.csv --json f0_estimation/outputs/E_STRING_swiftf0.json --plot f0_estimation/outputs/E_STRING_swiftf0.png
python f0_estimation/main.py --audio f0_estimation/data/TwinkleTwinkleLittleStar.wav --method swiftf0 --onset-delta 0.12 --onset-wait 25 --csv f0_estimation/outputs/TwinkleTwinkleLittleStar_swiftf0.csv --json f0_estimation/outputs/TwinkleTwinkleLittleStar_swiftf0.json --plot f0_estimation/outputs/TwinkleTwinkleLittleStar_swiftf0.png
python f0_estimation/examples/open_string_check.py --method swiftf0
python f0_estimation/examples/twinkle_demo_check.py --method swiftf0
python f0_estimation/examples/open_string_check.py --method pyin
python f0_estimation/examples/open_string_check.py --method autocorr
```

Expected behavior:

- Script completes without exceptions.
- Each estimator returns a non-empty F0 contour.
- A and E open-string checks pass within +/-50 cents.
- Intonation metrics are printed.
- Onset and phrase summaries are printed.

Current observed open-string medians:

| Method | A string | E string |
| --- | ---: | ---: |
| SwiftF0 | 437.89 Hz (-8.3 c) | 654.48 Hz (-12.6 c) |
| pYIN | 442.55 Hz (+10.0 c) | 663.08 Hz (+10.0 c) |
| Autocorr | 441.38 Hz (+5.4 c) | 662.21 Hz (+7.7 c) |

## Known Limitations

- Fine-grained estimator parameters are not exposed as command-line arguments.
- Reference-free cents can look good even if the played note is wrong relative to a score.
- Onset detection needs tuning per exercise type.
