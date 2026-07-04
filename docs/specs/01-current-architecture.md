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

Path: `dtw/align_demo.py`

This demo:

1. Parses `MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml` into note events.
2. Generates deterministic synthetic F0 or loads an F0 CSV.
3. Resamples score and performance to a common grid.
4. Uses DTW over clipped cents distance with a small temporal cost.
5. Emits per-note onset, pitch, duration, and feedback label exports.

The current version is the short interview demo. Long Bach alignment experiments are intentionally kept out of the tracked demo path.

## Data Policy

Small demo audio clips used by the F0 prototype are tracked in git. Large generated outputs, datasets, archives, long recordings, SoundFonts, and binary render artifacts are ignored.

This keeps the repository lightweight and suitable for GitHub while leaving enough data to run the main F0 demo.

## Current Pain Points

- Entry points are nested and require changing directories.
- Script parameters are hardcoded.
- F0 output is too verbose for a polished demo.
- MusicXML rendering depends on untracked SoundFonts.
- The Twinkle MusicXML example currently renders to an unexpectedly long MIDI.
- DTW has a short controlled alignment example; the next gap is making real-audio alignment more robust.

## Target Architecture

The next architecture should expose root-level commands:

```powershell
python -m mir_demo f0 --audio f0_estimation/data/A_STRING.wav --method swiftf0
python -m mir_demo musicxml --score MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml
python -m mir_demo align --score MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml --mode synthetic
```

The internal package can then share common utilities for audio loading, F0 estimation, intonation metrics, and tabular exports.
