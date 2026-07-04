# F0 Review

## Review Date

2026-07-04

## Summary

The F0 subsystem is a good prototype foundation. The estimator abstraction is clear, the available estimator set is relevant for violin MIR work, and the new A/E open-string checks give the project a concrete validation story.

## What Is Working Well

- A common `BaseF0Estimator` interface makes estimator comparison easy.
- `AutocorrEstimator`, `PyYINEstimator`, `CrepeEstimator`, and `SwiftF0Estimator` cover classic DSP, probabilistic DSP, and neural approaches.
- Reference-free intonation metrics are simple and explainable.
- Open-string violin clips now validate expected A4 and E5 behavior.
- CLI defaults now point to violin data instead of unrelated audio.

## Changes Made In This Review

- Removed non-violin `HB-1.wav`, `HB-2.wav`, and `HB-3.wav`.
- Added `AudioIO.load_audio_mono` for reusable audio loading.
- Added `EstimatorFactory.create_estimator` with lazy imports for optional heavy estimators.
- Made SwiftF0 dependency failure explicit and friendlier.
- Added CREPE confidence masking.
- Replaced the hardcoded F0 demo with an argparse CLI.
- Added `f0_estimation/examples/open_string_check.py`.
- Added a focused F0 README.

## Validation Results

| Method | A string median | A cents | E string median | E cents | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| SwiftF0 | 437.89 Hz | -8.3 c | 654.48 Hz | -12.6 c | PASS |
| pYIN | 442.55 Hz | +10.0 c | 663.08 Hz | +10.0 c | PASS |
| Autocorr | 441.38 Hz | +5.4 c | 662.21 Hz | +7.7 c | PASS |

The current smoke test threshold is +/-50 cents with at least 20% voiced frames after trimming 0.5 seconds from the attack and release edges.

## Remaining Risks

- The current intonation score is reference-free. It cannot detect a musically wrong note if the performed pitch is itself stable and close to an equal-tempered note.
- Open strings are easier than real violin phrases because they are sustained and monophonic.
- CREPE has not yet been included in the quick validation table because it is slower and heavier.
- No regression test framework is wired yet; the open-string checker is currently a runnable smoke test.
- Onset detection still needs exercise-specific tuning.

## Recommended Next Slice

1. Add CSV/JSON export to `f0_estimation/main.py`.
2. Add a diagnostic plot: waveform, F0 contour, nearest note, and cents error.
3. Convert `open_string_check.py` into a pytest regression test while keeping it runnable as a demo.
4. Add a short score-aware intonation example using MusicXML target notes.
