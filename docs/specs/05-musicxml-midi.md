# MusicXML2MIDI Spec

## Purpose

Provide a clean, configurable demo that turns a score file into reference MIDI and optional synthesized WAV. The demo supports the future score-aware alignment story without requiring the F0 pipeline to be complete end to end.

## Inputs

- MusicXML input: `.musicxml`, `.xml`, or compressed `.mxl`
- Optional SoundFont: local `.sf2`, required only for WAV rendering
- CLI configuration: output directory, sample rate, instrument name, and `--midi-only`

## Outputs

Generated artifacts are written to `MusicXML2MIDI/output/`, which is ignored by git:

- `<score>_<instrument>.mid`
- `<score>_<instrument>_<soundfont>_<sample-rate>hz.wav`

The output names are deterministic for the selected score, instrument, SoundFont, and sample rate.

## Flow

```text
MusicXML/MXL score
  -> music21 parse and duration diagnostics
  -> optional music21 instrument stamping
  -> music21 MIDI export
  -> optional FluidSynth render with local SoundFont
  -> MIDI/WAV files in MusicXML2MIDI/output/
```

## Current Implementation

- CLI entrypoint: `MusicXML2MIDI/musicxml_to_violin_audio.py`
- Default score: `MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml`
- Default output directory: `MusicXML2MIDI/output/`
- Default instrument name: `Violin`
- Default sample rate: `44100`

Validation behavior:

- Missing score returns a clear `score not found` error.
- Missing SoundFont returns a clear `soundfont not found` error.
- Missing FluidSynth returns a clear setup error unless `--midi-only` is used.

## Limitations

- WAV quality depends on the user's local SoundFont.
- `music21` MIDI export is sufficient for reference demos but not yet a production-grade expressive renderer.
- The existing `TwinkleTwinkleLittleStar.mxl` is long: 686 quarter notes and about 688 seconds after MIDI export. It is kept as a larger parsing example, not the default demo fixture.
- No score-to-performance alignment is performed in this module yet.

## Future DTW/Alignment Relationship

This module should eventually feed the DTW/alignment layer with reference timing and pitch data derived from the same score used to synthesize MIDI/WAV. Near-term alignment work should add exports for note onset, offset, pitch, measure, and beat positions so performed F0 tracks can be compared against score-derived targets.
