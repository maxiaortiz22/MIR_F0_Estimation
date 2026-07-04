import sys
import subprocess
import shutil
from pathlib import Path

from music21 import converter
from mido import MidiFile


# ---------- Configuration ----------
INPUT_MUSICXML = r"musicxml\TwinkleTwinkleLittleStar.mxl"
SOUNDFONT = r"soundfont\violin.sf2"
OUTPUT_DIR = r".\output"
SAMPLE_RATE = 44100


def get_musicxml_duration(musicxml_path: Path) -> tuple[float | None, float, any]:
    """Get the duration of a MusicXML file. Returns (seconds or None, quarterLength, score)."""
    import math
    score = converter.parse(str(musicxml_path))
    seconds = score.seconds if not math.isnan(score.seconds) else None
    quarter_length = score.duration.quarterLength
    return seconds, quarter_length, score


def get_midi_duration(midi_path: Path) -> float:
    """Get the duration of a MIDI file in seconds."""
    mid = MidiFile(str(midi_path))
    return mid.length


def convert_musicxml_to_midi(score, midi_out_path: Path) -> None:
    """Convert a music21 score to MIDI."""
    midi_out_path.parent.mkdir(parents=True, exist_ok=True)
    score.write("midi", fp=str(midi_out_path))


def render_midi_to_wav(soundfont: Path, midi_in: Path, wav_out: Path, sample_rate: int) -> None:
    """Render a MIDI file to WAV using FluidSynth."""
    wav_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "fluidsynth", "-ni", "-q",
        "-a", "file",
        "-o", "synth.reverb.active=false",
        "-o", "synth.chorus.active=false",
        "-F", str(wav_out),
        "-T", "wav",
        "-r", str(sample_rate),
        str(soundfont),
        str(midi_in),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"fluidsynth failed ({result.returncode}): {result.stderr.strip()}")


def main() -> int:
    input_path = Path(INPUT_MUSICXML).resolve()
    soundfont_path = Path(SOUNDFONT).resolve()
    output_dir = Path(OUTPUT_DIR).resolve()

    # Validation
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1
    if not soundfont_path.exists():
        print(f"Error: SoundFont not found: {soundfont_path}", file=sys.stderr)
        return 1
    if shutil.which("fluidsynth") is None:
        print("Error: 'fluidsynth' is not installed or not in PATH.", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    # Output paths
    stem = input_path.stem
    midi_path = output_dir / f"{stem}.mid"
    wav_path = output_dir / f"{stem}_{soundfont_path.stem}.wav"

    # Parse MusicXML and show duration
    print(f"[1/2] Parsing MusicXML: {input_path.name}")
    musicxml_seconds, quarter_length, score = get_musicxml_duration(input_path)
    if musicxml_seconds is not None:
        print(f"      MusicXML duration: {musicxml_seconds:.2f}s ({musicxml_seconds/60:.2f} min)")
    else:
        print(f"      MusicXML duration: unknown (no tempo), quarterLength: {quarter_length:.2f}")
    
    # Convert to MIDI
    print(f"      Converting to MIDI: {midi_path.name}")
    convert_musicxml_to_midi(score, midi_path)
    
    # Show MIDI duration
    midi_duration = get_midi_duration(midi_path)
    print(f"      MIDI duration: {midi_duration:.2f}s ({midi_duration/60:.2f} min)")

    # Step 2: MIDI -> WAV
    print(f"[2/2] Rendering WAV with SoundFont: {midi_path.name} -> {wav_path.name}")
    render_midi_to_wav(soundfont_path, midi_path, wav_path, SAMPLE_RATE)

    print(f"\nDone!")
    print(f"  MIDI: {midi_path}")
    print(f"  WAV:  {wav_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
