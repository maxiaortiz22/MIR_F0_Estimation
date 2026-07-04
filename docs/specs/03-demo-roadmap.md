# Demo Roadmap

## Demo 1: F0 And Intonation

Status: strongest current demo. Open-string validation, a short Twinkle melody clip, and CSV/JSON/PNG exports are now in place.

Goal:

Show a short violin recording, estimate F0, compute intonation metrics, detect onsets, and export a compact summary.

Current implementation slice:

- `--csv`, `--json`, and `--plot` options export frame data, summary metrics, and diagnostics.
- `TwinkleTwinkleLittleStar.wav` demonstrates a changing pitch contour beyond open-string checks.

Next implementation slice:

- Add a root-level package entrypoint after the script API stabilizes.
- Add regression tests around the open-string checks.

## Demo 2: MusicXML To Reference Audio

Status: CLI demo is now available with deterministic output paths and a short curated score.

Goal:

Convert a MusicXML score into MIDI and optionally render a reference WAV for alignment experiments.

Current implementation slice:

- CLI arguments cover score, SoundFont, sample rate, output directory, instrument name, and MIDI-only mode.
- The SoundFont requirement is documented for WAV rendering.
- A short curated Twinkle fixture is the default demo score; the older long Twinkle file is documented as unsuitable for interviews.

Next implementation slice:

- Export score note events as CSV/JSON for the alignment layer.
- Add a tiny regression check around the curated MusicXML fixture duration.

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
