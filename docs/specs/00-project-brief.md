# Project Brief

## Product Context

The target product is an interactive violin learning application for children. A learner records a performance, the system analyzes pitch, intonation, rhythm, tempo, and alignment against a score, then returns actionable visual feedback.

This repository focuses on the MIR and DSP layer that would sit behind that product.

## Portfolio Goal

Build an interview-ready prototype that shows practical command of:

- Violin F0 estimation.
- Intonation scoring in cents.
- Onset and phrase analysis.
- MusicXML parsing and rendering.
- Score-audio alignment experiments.
- Clear documentation, reproducible environments, and demo commands.

## Current Scope

The strongest current path is the F0 pipeline:

1. Load mono audio from a WAV file.
2. Estimate F0 using one of several estimators.
3. Convert F0 to nearest equal-tempered MIDI note.
4. Compute cents error and simple intonation percentages.
5. Detect onsets and phrase regions.

MusicXML rendering and DTW alignment exist as separate prototypes. They should be preserved, documented, and gradually integrated into the root demo workflow.

## Non-Goals For The Current Prototype

- Real-time browser audio capture.
- Production model serving.
- Full score-following with robust repeats, ornaments, and expressive timing.
- A polished frontend.
- Full dataset packaging inside git.

## Success Criteria

The next stable version should let an interviewer run a short command from the repository root and see:

- Which estimator was used.
- A compact F0 and intonation summary.
- Onset and phrase counts.
- Optional CSV/JSON export.
- Optional diagnostic plot.
- Clear explanation of the current algorithmic tradeoffs.
