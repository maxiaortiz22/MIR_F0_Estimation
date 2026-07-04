# F0 Estimation

This folder contains the strongest current part of the project: F0 estimation and reference-free intonation analysis for monophonic violin audio.

## Data

Tracked validation clips:

| File | Expected note | Expected F0 |
| --- | --- | --- |
| `data/A_STRING.wav` | A4 | 440.00 Hz |
| `data/E_STRING.wav` | E5 | 659.26 Hz |

The old `HB-*` clips were removed because they were not violin examples.

## Run The Demo

From the repository root:

```powershell
conda activate musicdsp
python f0_estimation/main.py --method swiftf0
```

Useful variants:

```powershell
python f0_estimation/main.py --audio f0_estimation/data/E_STRING.wav --method pyin
python f0_estimation/main.py --method autocorr --print-frames --max-frame-lines 20
python f0_estimation/main.py --method swiftf0 --skip-onsets
python f0_estimation/main.py --method crepe --skip-onsets
```

If `--method crepe` reports that `crepe` is missing, PowerShell is probably using the base Conda Python instead of `musicdsp`. Check with:

```powershell
python -c "import sys; print(sys.executable)"
```

Expected environment for the full demo:

```text
C:\Users\maxia\anaconda3\envs\musicdsp\python.exe
```

You can also bypass activation explicitly:

```powershell
& C:\Users\maxia\anaconda3\envs\musicdsp\python.exe f0_estimation/main.py --method crepe --skip-onsets
```

CREPE is significantly slower than SwiftF0, pYIN, and autocorrelation on CPU because it runs a TensorFlow model.

## Run Open-String Checks

```powershell
python f0_estimation/examples/open_string_check.py --method swiftf0
python f0_estimation/examples/open_string_check.py --method pyin
python f0_estimation/examples/open_string_check.py --method autocorr
```

Current observed results on the local `musicdsp` environment:

| Method | A string median | A cents | E string median | E cents |
| --- | ---: | ---: | ---: | ---: |
| SwiftF0 | 437.89 Hz | -8.3 c | 654.48 Hz | -12.6 c |
| pYIN | 442.55 Hz | +10.0 c | 663.08 Hz | +10.0 c |
| Autocorr | 441.38 Hz | +5.4 c | 662.21 Hz | +7.7 c |

All three estimators pass the current open-string smoke test with a +/-50 cent tolerance.

## Implementation Notes

- `BaseF0Estimator` defines the estimator contract.
- `EstimatorFactory` creates estimators by name and imports heavy optional dependencies lazily.
- `AudioIO` loads stereo/mono audio as mono float32.
- `Intonation` maps F0 to nearest equal-tempered pitch and cents error.
- `OnsetPhraseSegmenter` provides simple onset and phrase boundaries.

The current intonation metric is reference-free: it measures distance to the nearest equal-tempered note, not distance to the intended score note.
