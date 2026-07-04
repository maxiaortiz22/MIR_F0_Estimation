# DTW Alignment Demo

This folder now has a small, reproducible score-to-performance alignment demo for a violin learning app.

The main demo uses the same short score as `MusicXML2MIDI`:

```text
MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml
```

That keeps the interview story integrated:

```text
MusicXML -> reference note events -> synthetic/performed F0 -> DTW -> per-note feedback
```

The older `dtw/main.py` and Bach assets are kept as legacy prototype material. They are not the primary demo path.

## Why Synthetic First

Real audio alignment depends on recording quality, F0 estimator settings, latency, silence trimming, and tempo differences. The synthetic mode creates a deterministic performance F0 contour from the score events with small timing and pitch deviations. That makes the core DTW behavior easy to run, inspect, and explain without large audio files.

## Run

From the repository root:

```powershell
python dtw/align_demo.py --score MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml --mode synthetic --plot
```

The default score is already `DemoTwinkleShort.musicxml`, so this shorter command is equivalent:

```powershell
python dtw/align_demo.py --mode synthetic --plot
```

Experimental F0 CSV mode:

```powershell
python dtw/align_demo.py --mode f0-csv --score MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml --f0-csv f0_estimation/outputs/TwinkleTwinkleLittleStar_swiftf0.csv --plot
```

The F0 CSV reader accepts either `time_s,f0_hz` from the current F0 estimator or `t,f0_hz` from the older DTW prototype.

## Outputs

Generated files go to `dtw/output/`, which is ignored by git:

- `alignment_notes.csv`: one row per score note with expected pitch/time, aligned time, onset error, median cents error, duration ratio, and feedback label.
- `alignment_summary.json`: score metadata, tempo marks, aggregate alignment metrics, label counts, and per-note rows.
- `alignment_plot.png`: score reference F0, performance F0, and per-note cents feedback.

## Feedback Labels

The current labels are intentionally simple:

- `OK`: onset and pitch are within demo thresholds.
- `EARLY` / `LATE`: aligned onset differs by at least 50 ms.
- `SHARP` / `FLAT`: median pitch differs by at least 25 cents.
- `MISSED`: no voiced/aligned data could be assigned to the note.

For the interview demo, the label is a compact explanation of what a violin student might see after playing a phrase.

## Connection To The Violin App

This demo is the score-aware counterpart to the F0 estimator. The F0 module can produce a time series from violin audio; this DTW module compares a performed contour against intended score events and exports per-note feedback that an app UI could render above the score.

The next production step is to replace synthetic performance F0 with real recorded F0 more reliably: trim silence, estimate tempo/latency, detect missed or extra notes, and feed richer MusicXML positions such as measure and beat into the output.
