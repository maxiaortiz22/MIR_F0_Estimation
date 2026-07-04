# F0 Pipeline Spec

## Purpose

Estimate violin F0 and derive beginner-friendly intonation and segmentation metrics from short monophonic recordings.

## Inputs

- Audio file: WAV preferred.
- Sample rate: preserve source sample rate by default.
- Channels: stereo is downmixed to mono.
- Estimator: `autocorr`, `pyin`, `crepe`, or `swiftf0`.

## Outputs

Current outputs:

- Per-frame timestamp in seconds.
- Per-frame F0 in Hz.
- Reference-free intonation percentages within +/-25, +/-50, and +/-100 cents.
- Nearest equal-tempered note labels.
- Onset times.
- Phrase boundaries.

Planned outputs:

- CSV with `time_s`, `f0_hz`, `nearest_note`, `cents_error`.
- JSON summary with estimator, audio metadata, voicing rate, intonation metrics, onset count, and phrase count.
- Optional PNG plot for interview demos.

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
cd f0_estimation
python main.py
```

Expected behavior:

- Script completes without exceptions.
- SwiftF0 returns a non-empty F0 contour.
- Intonation metrics are printed.
- Onset and phrase summaries are printed.

## Known Limitations

- Current demo prints every voiced frame.
- There is no root-level CLI yet.
- Estimator parameters are not exposed as command-line arguments.
- Reference-free cents can look good even if the played note is wrong relative to a score.
- Onset detection needs tuning per exercise type.
