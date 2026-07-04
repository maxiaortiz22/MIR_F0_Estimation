# MusicXML2MIDI

Clean interview demo for converting a MusicXML score into a deterministic MIDI file and, when a local SoundFont and FluidSynth are available, rendering that MIDI to WAV.

The script is intentionally small: it validates local inputs, prints score/MIDI duration diagnostics, stamps a requested MIDI instrument, and writes generated artifacts to `MusicXML2MIDI/output/`.

## Dependencies

Python packages:

```powershell
pip install -r MusicXML2MIDI/requirements.txt
```

External tools for WAV rendering:

- [FluidSynth](https://www.fluidsynth.org/) available on `PATH`
- A local `.sf2` SoundFont, for example `MusicXML2MIDI/soundfont/violin.sf2`

SoundFonts and rendered audio are intentionally ignored by git.

## MIDI-Only Demo

Run from the repository root:

```powershell
python MusicXML2MIDI/musicxml_to_violin_audio.py --midi-only
```

Or pass a specific score:

```powershell
python MusicXML2MIDI/musicxml_to_violin_audio.py --score MusicXML2MIDI/musicxml/TwinkleTwinkleLittleStar.mxl --midi-only
```

The default score is `MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml`, a short curated fixture that renders in about eight seconds.

## WAV Render

```powershell
python MusicXML2MIDI/musicxml_to_violin_audio.py `
  --score MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml `
  --soundfont MusicXML2MIDI/soundfont/violin.sf2 `
  --sample-rate 44100
```

Useful options:

- `--output-dir`: output directory, default `MusicXML2MIDI/output/`
- `--instrument-name`: music21 instrument name stamped into the MIDI, default `Violin`
- `--midi-only`: skip SoundFont and FluidSynth checks

## Outputs

Generated files are deterministic for a given score, instrument, SoundFont, and sample rate:

- `MusicXML2MIDI/output/<score>_<instrument>.mid`
- `MusicXML2MIDI/output/<score>_<instrument>_<soundfont>_<sample-rate>hz.wav`

`MusicXML2MIDI/output/` is ignored by git, along with `*.sf2` and `*.wav`.

## Note About TwinkleTwinkleLittleStar.mxl

`TwinkleTwinkleLittleStar.mxl` is not a short demo score. In music21 it has 686 quarter notes, 3065 note/rest events, two parts, and tempo changes at 120, 80, and 120 BPM. The exported MIDI is about 688 seconds long. Keep it as a parsing stress/example file; use `DemoTwinkleShort.musicxml` for interviews.
