# MIR F0 Estimation

Prototype repository for music information retrieval experiments focused on violin performance analysis.

The current project explores the signal-processing core of an interactive violin learning product: estimating F0, intonation, onsets, phrase boundaries, MusicXML-to-audio rendering, and early score-audio alignment experiments.

## Why This Exists

This repository is being shaped as an interview-ready technical portfolio project. It demonstrates practical work on the same problems required by a violin learning app:

- F0 extraction from monophonic violin recordings.
- Reference-free intonation metrics in cents.
- Onset detection and phrase segmentation.
- MusicXML to MIDI/WAV rendering prototypes.
- Early DTW-based score-to-performance alignment experiments.

## Repository Layout

```text
f0_estimation/
  f0_estimation/
    BaseF0Estimator.py
    AutocorrEstimator.py
    PyYINEstimator.py
    CrepeEstimator.py
    SwiftF0Estimator.py
    Intonation.py
    OnsetPhraseSegmenter.py
  data/
    Small violin demo clips tracked in git.
  main.py

MusicXML2MIDI/
  musicxml_to_violin_audio.py
  musicxml/
  requirements.txt

dtw/
  main.py
  *.mxl

docs/specs/
  Lightweight SDD documentation for the current system and roadmap.
```

Large rendered audio, SoundFonts, dataset archives, and extracted datasets are intentionally ignored by git.

## Environment

The project targets the local Conda environment `musicdsp`. A curated reproducible environment file is provided:

```powershell
conda env create -f environment.yml
conda activate musicdsp
```

Some optional demos require external binaries or assets:

- `fluidsynth` must be available on `PATH` for MusicXML/MIDI rendering.
- SoundFont files are not committed because they are large binary assets.
- Full DTW datasets and long audio recordings are not committed.

## Run The Current F0 Demo

```powershell
python f0_estimation/main.py --method swiftf0
```

The current demo estimates F0 with SwiftF0, summarizes the contour, detects onsets/phrases, and computes reference-free intonation metrics against the nearest equal-tempered note.

Known current behavior:

- The default clip is `f0_estimation/data/A_STRING.wav`, a violin open A string.
- Per-frame output is available with `--print-frames`.
- The next step is to add CSV/JSON and plot outputs for interview demos.

## Validate Open-String Examples

```powershell
python f0_estimation/examples/open_string_check.py --method swiftf0
python f0_estimation/examples/open_string_check.py --method pyin
python f0_estimation/examples/open_string_check.py --method autocorr
python f0_estimation/examples/open_string_check.py --method crepe
```

The tracked violin validation clips are:

- `A_STRING.wav`: expected A4, 440.00 Hz.
- `E_STRING.wav`: expected E5, 659.26 Hz.

The former `HB-*` clips were removed because they were not violin recordings.

## Run The MusicXML Prototype

```powershell
cd MusicXML2MIDI
python musicxml_to_violin_audio.py
```

This parses MusicXML with `music21`, writes MIDI, and renders WAV with FluidSynth. This path is functional but still needs a cleaner command-line interface and a better curated short demo score.

## Run The DTW Prototype

```powershell
cd dtw
python main.py
```

The DTW path is an exploratory prototype. It is useful for documenting score-audio alignment work, but it is not yet the primary interview demo.

## Documentation

The SDD notes live in [docs/specs](docs/specs). Start with:

- [Project Brief](docs/specs/00-project-brief.md)
- [Current Architecture](docs/specs/01-current-architecture.md)
- [F0 Pipeline Spec](docs/specs/02-f0-pipeline.md)
- [Demo Roadmap](docs/specs/03-demo-roadmap.md)
- [F0 Review](docs/specs/04-f0-review.md)

## Near-Term Goals

1. Add root-level demo commands for F0, MusicXML rendering, and alignment.
2. Convert hardcoded script constants into CLI arguments.
3. Add compact CSV/JSON outputs for F0, intonation, onset, and phrase metrics.
4. Add plots suitable for interviews: waveform + F0 contour + nearest note + cents error.
5. Promote DTW alignment once a short, controlled score/audio example is reliable.
