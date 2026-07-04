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
  align_demo.py

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

Useful demo output commands:

```powershell
python f0_estimation/main.py --audio f0_estimation/data/A_STRING.wav --method swiftf0 --csv f0_estimation/outputs/A_STRING_swiftf0.csv --json f0_estimation/outputs/A_STRING_swiftf0.json --plot f0_estimation/outputs/A_STRING_swiftf0.png
python f0_estimation/main.py --audio f0_estimation/data/E_STRING.wav --method swiftf0 --csv f0_estimation/outputs/E_STRING_swiftf0.csv --json f0_estimation/outputs/E_STRING_swiftf0.json --plot f0_estimation/outputs/E_STRING_swiftf0.png
python f0_estimation/main.py --audio f0_estimation/data/TwinkleTwinkleLittleStar.wav --method swiftf0 --onset-delta 0.12 --onset-wait 25 --csv f0_estimation/outputs/TwinkleTwinkleLittleStar_swiftf0.csv --json f0_estimation/outputs/TwinkleTwinkleLittleStar_swiftf0.json --plot f0_estimation/outputs/TwinkleTwinkleLittleStar_swiftf0.png
```

Output artifacts:

- `--csv`: per-frame `time_s`, `f0_hz`, `nearest_note`, and `cents_error`.
- `--json`: audio summary, estimator, voicing rate, median/p05/p95 F0, intonation metrics, onset count, and phrase count.
- `--plot`: PNG with waveform, F0 contour, and cents error from the nearest equal-tempered note.

Known current behavior:

- The default clip is `f0_estimation/data/A_STRING.wav`, a violin open A string.
- Per-frame output is available with `--print-frames`.
- CSV/JSON/PNG outputs can be generated for interview demos.

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
- `TwinkleTwinkleLittleStar.wav`: short rendered violin melody for non-open-string F0 demos.

The melodic demo check validates that Twinkle produces voiced F0 over several expected notes:

```powershell
python f0_estimation/examples/twinkle_demo_check.py --method swiftf0
```

Twinkle uses lower onset sensitivity than the open-string defaults because repeated melodic notes have softer attacks than the first note of a sustained open string.

The former `HB-*` clips were removed because they were not violin recordings.

## Run The MusicXML Prototype

```powershell
cd MusicXML2MIDI
python musicxml_to_violin_audio.py
```

This parses MusicXML with `music21`, writes MIDI, and renders WAV with FluidSynth. This path is functional but still needs a cleaner command-line interface and a better curated short demo score.

## Run The DTW Alignment Demo

```powershell
python dtw/align_demo.py --score MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml --mode synthetic --plot
```

The primary DTW demo uses the same short `DemoTwinkleShort.musicxml` fixture as `MusicXML2MIDI`. It parses score events, generates or loads a performed F0 contour, runs DTW, and writes per-note feedback to `dtw/output/`.

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
3. Add regression tests around exported F0 demo artifacts.
4. Add root-level shortcuts for repeatable demo generation.
5. Promote DTW alignment once a short, controlled score/audio example is reliable.
