import argparse
import copy
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from mido import MidiFile
from music21 import converter, instrument, tempo


MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_SCORE = MODULE_DIR / "musicxml" / "DemoTwinkleShort.musicxml"
DEFAULT_SOUNDFONT = MODULE_DIR / "soundfont" / "violin.sf2"
DEFAULT_OUTPUT_DIR = MODULE_DIR / "output"
DEFAULT_SAMPLE_RATE = 44_100
DEFAULT_INSTRUMENT = "Violin"
LONG_SCORE_QUARTER_LENGTH = 120


class CliError(ValueError):
    """Error caused by invalid user input or local setup."""


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"must be an integer: {value}") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a MusicXML score to MIDI and optionally render a WAV with FluidSynth."
    )
    parser.add_argument(
        "--score",
        type=Path,
        default=DEFAULT_SCORE,
        help=f"MusicXML/MXL input score. Default: {DEFAULT_SCORE}",
    )
    parser.add_argument(
        "--soundfont",
        type=Path,
        default=DEFAULT_SOUNDFONT,
        help=f"SoundFont used for WAV rendering. Required unless --midi-only. Default: {DEFAULT_SOUNDFONT}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for generated MIDI/WAV files. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--sample-rate",
        type=positive_int,
        default=DEFAULT_SAMPLE_RATE,
        help=f"WAV sample rate for FluidSynth rendering. Default: {DEFAULT_SAMPLE_RATE}",
    )
    parser.add_argument(
        "--instrument-name",
        default=DEFAULT_INSTRUMENT,
        help=(
            "music21 instrument name to stamp into the exported MIDI. "
            "Use an empty string to keep the score instrumentation. Default: Violin"
        ),
    )
    parser.add_argument(
        "--midi-only",
        action="store_true",
        help="Only write MIDI; skip SoundFont and FluidSynth validation/rendering.",
    )
    return parser.parse_args(argv)


def resolve_path(path: Path) -> Path:
    return path.expanduser().resolve()


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-._")
    return slug or "score"


def validate_inputs(score_path: Path, soundfont_path: Path, midi_only: bool) -> None:
    if not score_path.exists():
        raise CliError(f"score not found: {score_path}")
    if not score_path.is_file():
        raise CliError(f"score path is not a file: {score_path}")

    if midi_only:
        return

    if not soundfont_path.exists():
        raise CliError(f"soundfont not found: {soundfont_path}")
    if not soundfont_path.is_file():
        raise CliError(f"soundfont path is not a file: {soundfont_path}")
    if shutil.which("fluidsynth") is None:
        raise CliError("fluidsynth is not installed or is not available in PATH")


def load_score(musicxml_path: Path) -> Any:
    try:
        return converter.parse(str(musicxml_path))
    except Exception as exc:  # music21 raises several parser-specific exceptions.
        raise CliError(f"could not parse score '{musicxml_path}': {exc}") from exc


def get_musicxml_duration(score: Any) -> tuple[float | None, float]:
    seconds = score.seconds
    if seconds is None or not math.isfinite(seconds):
        seconds = None
    return seconds, float(score.duration.quarterLength)


def get_tempo_marks(score: Any) -> list[str]:
    marks = []
    for mark in score.recurse().getElementsByClass(tempo.MetronomeMark):
        bpm = "unknown" if mark.number is None else f"{mark.number:g}"
        offset = float(mark.getOffsetInHierarchy(score))
        marks.append(f"{bpm} BPM @ ql={offset:g}")
    return marks


def apply_instrument(score: Any, instrument_name: str) -> None:
    clean_name = instrument_name.strip()
    if not clean_name:
        return

    try:
        instrument_template = instrument.fromString(clean_name)
    except Exception as exc:
        raise CliError(f"unknown music21 instrument name '{instrument_name}'") from exc

    parts = list(score.parts)
    if not parts:
        score.insert(0, instrument_template)
        return

    for part in parts:
        part.insert(0, copy.deepcopy(instrument_template))


def get_midi_duration(midi_path: Path) -> float:
    return MidiFile(str(midi_path)).length


def convert_musicxml_to_midi(score: Any, midi_out_path: Path) -> None:
    midi_out_path.parent.mkdir(parents=True, exist_ok=True)
    score.write("midi", fp=str(midi_out_path))


def render_midi_to_wav(soundfont: Path, midi_in: Path, wav_out: Path, sample_rate: int) -> None:
    wav_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "fluidsynth",
        "-ni",
        "-q",
        "-a",
        "file",
        "-o",
        "synth.reverb.active=false",
        "-o",
        "synth.chorus.active=false",
        "-F",
        str(wav_out),
        "-T",
        "wav",
        "-r",
        str(sample_rate),
        str(soundfont),
        str(midi_in),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "no FluidSynth output"
        raise RuntimeError(f"fluidsynth failed ({result.returncode}): {message}")


def build_output_paths(
    score_path: Path,
    soundfont_path: Path,
    output_dir: Path,
    instrument_name: str,
    sample_rate: int,
) -> tuple[Path, Path]:
    instrument_slug = slugify(instrument_name) if instrument_name.strip() else "original"
    score_slug = slugify(score_path.stem)
    midi_path = output_dir / f"{score_slug}_{instrument_slug}.mid"
    wav_path = output_dir / (
        f"{score_slug}_{instrument_slug}_{slugify(soundfont_path.stem)}_{sample_rate}hz.wav"
    )
    return midi_path, wav_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    score_path = resolve_path(args.score)
    soundfont_path = resolve_path(args.soundfont)
    output_dir = resolve_path(args.output_dir)

    try:
        validate_inputs(score_path, soundfont_path, args.midi_only)

        midi_path, wav_path = build_output_paths(
            score_path,
            soundfont_path,
            output_dir,
            args.instrument_name,
            args.sample_rate,
        )

        print(f"[1/2] Parsing MusicXML: {score_path}")
        score = load_score(score_path)
        musicxml_seconds, quarter_length = get_musicxml_duration(score)
        tempo_marks = get_tempo_marks(score)

        if musicxml_seconds is None:
            print(f"      MusicXML symbolic length: {quarter_length:.2f} quarter notes")
        else:
            print(
                f"      MusicXML duration: {musicxml_seconds:.2f}s "
                f"({musicxml_seconds / 60:.2f} min); quarterLength={quarter_length:.2f}"
            )
        if tempo_marks:
            print(f"      Tempo marks: {', '.join(tempo_marks[:5])}")
            if len(tempo_marks) > 5:
                print(f"      Tempo marks: ... {len(tempo_marks) - 5} more")
        else:
            print("      Tempo marks: none found; MIDI export may use a default tempo")
        if quarter_length > LONG_SCORE_QUARTER_LENGTH:
            print(
                "      Warning: this is a long score for an interview demo. "
                "Consider MusicXML2MIDI/musicxml/DemoTwinkleShort.musicxml."
            )

        print(f"      Applying instrument: {args.instrument_name or 'score default'}")
        apply_instrument(score, args.instrument_name)

        print(f"      Writing MIDI: {midi_path}")
        convert_musicxml_to_midi(score, midi_path)
        midi_duration = get_midi_duration(midi_path)
        print(f"      MIDI duration: {midi_duration:.2f}s ({midi_duration / 60:.2f} min)")

        if args.midi_only:
            print("[2/2] Skipping WAV render (--midi-only)")
            print("\nDone.")
            print(f"  MIDI: {midi_path}")
            return 0

        print(f"[2/2] Rendering WAV with SoundFont: {soundfont_path}")
        render_midi_to_wav(soundfont_path, midi_path, wav_path, args.sample_rate)

        print("\nDone.")
        print(f"  MIDI: {midi_path}")
        print(f"  WAV:  {wav_path}")
        return 0
    except CliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
