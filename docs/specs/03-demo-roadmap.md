# Demo Roadmap

## Demo 1: F0 And Intonation

Status: strongest current demo.

Goal:

Show a short violin recording, estimate F0, compute intonation metrics, detect onsets, and export a compact summary.

Next implementation slice:

- Add root-level CLI.
- Add `--audio`, `--method`, `--summary-only`, `--csv`, and `--plot` options.
- Print a concise summary by default.
- Keep verbose per-frame output behind a flag.

## Demo 2: MusicXML To Reference Audio

Status: functional but needs cleanup.

Goal:

Convert a MusicXML score into MIDI and optionally render a reference WAV for alignment experiments.

Next implementation slice:

- Add CLI arguments for score, SoundFont, sample rate, and output directory.
- Document the SoundFont requirement.
- Replace or fix the current Twinkle example if its duration remains unsuitable.

## Demo 3: Score-Audio Alignment

Status: exploratory.

Goal:

Align performed F0 against score-derived reference pitch and produce per-note feedback.

Next implementation slice:

- Create or select a short controlled score/audio pair.
- Export alignment metrics as CSV and JSON.
- Limit the demo to a short clip so it runs quickly.
- Make DTW diagnostics visible: path cost, per-note cents, onset error, and dropped/unvoiced regions.

## Demo 4: Product-Like Feedback Summary

Status: planned.

Goal:

Turn raw metrics into feedback that resembles an educational app.

Example output:

```json
{
  "intonation_score": 82.5,
  "tempo_stability": "not_available_yet",
  "main_feedback": "Most sustained notes are close; the second phrase drifts sharp.",
  "events": [
    {
      "time_s": 1.24,
      "type": "intonation",
      "severity": "medium",
      "message": "This note is about 38 cents sharp."
    }
  ]
}
```

## Interview Narrative

The intended story:

1. Start with the raw DSP problem: clean F0 estimation on violin.
2. Compare estimator options and explain tradeoffs.
3. Show intonation metrics in cents.
4. Connect onsets and phrase segmentation to student feedback.
5. Explain how MusicXML and DTW extend this into score-aware assessment.
6. Discuss production steps: CLI, tests, latency, ONNX/TorchScript, containers, and monitoring.
