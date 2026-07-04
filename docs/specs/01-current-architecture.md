# Current Architecture

## Modules

### F0 Estimation

Path: `f0_estimation/f0_estimation`

The F0 package defines a common estimator interface:

- `BaseF0Estimator`: abstract estimator contract.
- `AutocorrEstimator`: classic time-domain autocorrelation baseline.
- `PyYINEstimator`: librosa pYIN wrapper.
- `CrepeEstimator`: CREPE neural pitch estimator wrapper.
- `SwiftF0Estimator`: SwiftF0 wrapper.
- `Intonation`: Hz to MIDI conversion, nearest-note mapping, cents metrics.
- `OnsetPhraseSegmenter`: onset detection and phrase segmentation using librosa.

The current script entrypoint is `f0_estimation/main.py`.

### MusicXML To MIDI/WAV

Path: `MusicXML2MIDI/musicxml_to_violin_audio.py`

This prototype:

1. Parses MusicXML with `music21`.
2. Exports MIDI.
3. Uses FluidSynth plus a SoundFont to render WAV.
4. Prints MusicXML and MIDI duration information.

The script currently depends on hardcoded paths and local SoundFont assets.

### DTW Alignment

Path: `dtw/main.py`

This prototype:

1. Parses a MusicXML reference into note events.
2. Computes or loads an F0 time series.
3. Resamples score and audio to a common grid.
4. Uses DTW over cents distance.
5. Emits per-note median cents and onset error estimates.

The current version is exploratory and uses long recordings, so it is not yet the primary demo.

## Data Policy

Small demo audio clips used by the F0 prototype are tracked in git. Large generated outputs, datasets, archives, long recordings, SoundFonts, and binary render artifacts are ignored.

This keeps the repository lightweight and suitable for GitHub while leaving enough data to run the main F0 demo.

## Current Pain Points

- Entry points are nested and require changing directories.
- Script parameters are hardcoded.
- F0 output is too verbose for a polished demo.
- MusicXML rendering depends on untracked SoundFonts.
- The Twinkle MusicXML example currently renders to an unexpectedly long MIDI.
- DTW needs a short controlled alignment example before being shown as a polished result.

## Target Architecture

The next architecture should expose root-level commands:

```powershell
python -m mir_demo f0 --audio f0_estimation/data/HB-1.wav --method swiftf0
python -m mir_demo musicxml --score MusicXML2MIDI/musicxml/TwinkleTwinkleLittleStar.mxl
python -m mir_demo align --score dtw/bwv1001.mxl --audio path/to/audio.wav
```

The internal package can then share common utilities for audio loading, F0 estimation, intonation metrics, and tabular exports.
