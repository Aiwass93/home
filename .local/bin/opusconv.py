#!/usr/bin/env python3
"""
opusconv - Convert audio files to Opus format.

Usage: opusconv.py <source_dir> [source_dir2 ...]

Features:
    - Converts lossless (FLAC, WAV, etc.) at 96k
    - Converts lossy (MP3, M4A, etc.) at 192k
    - Splits single-file albums using CUE sheets
    - Copies and refreshes album covers

Requires: opusencode.py, cueparse.py, covercp.py, coverfix.py in PATH or same directory.
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path
import glob

# --- CONFIGURATION ---
DEST_DIR = Path("/home/alice/opus/")
SCRIPT_DIR = Path(__file__).parent.resolve()

EXT_LOSSLESS = {'.flac', '.wav', '.aiff', '.ape', '.alac', '.tak'}
EXT_LOSSY = {'.mp3', '.m4a', '.aac', '.ogg', '.wma'}

def get_bitrate(extension):
    """Determine target bitrate based on source format."""
    ext = extension.lower()
    if ext in EXT_LOSSLESS:
        return "96k"
    if ext in EXT_LOSSY:
        return "192k"
    return None

def sanitize_filename(name):
    """Remove illegal characters from filenames."""
    return re.sub(r'[<>:"/\\|?*]', '_', str(name)).strip()

def run_script(name, args):
    """Run a helper script from the same directory or PATH."""
    script = SCRIPT_DIR / name
    if not script.exists():
        script = name  # Try PATH

    cmd = [sys.executable, str(script)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def run_cueparse(cue_path):
    """Parse CUE file using cueparse.py, return parsed data or None."""
    result = run_script('cueparse.py', [str(cue_path)])
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

def run_opusencode(input_path, output_path, bitrate, start=None, duration=None, metadata=None):
    """Encode file using opusencode.py."""
    args = ['-i', str(input_path), '-o', str(output_path), '-b', bitrate]

    if start is not None:
        args.extend(['-s', str(start)])
    if duration is not None:
        args.extend(['-d', str(duration)])

    for key, value in (metadata or {}).items():
        if value:
            args.extend(['-m', f'{key}={value}'])

    result = run_script('opusencode.py', args)
    return result.returncode == 0

def run_covercp(source, dest):
    """Copy cover using covercp.py."""
    result = run_script('covercp.py', [str(source), str(dest)])
    return result.returncode == 0

def run_coverfix(dest):
    """Refresh cover using coverfix.py."""
    result = run_script('coverfix.py', [str(dest)])
    return result.returncode == 0

def find_audio_for_cue(cue_dir, ref_filename):
    """Find the actual audio file referenced by CUE."""
    ref_path = cue_dir / ref_filename
    if ref_path.exists():
        return ref_path

    ref_stem = Path(ref_filename).stem
    for ext in ['.flac', '.ape', '.wav', '.tak', '.mp3', '.m4a']:
        candidate = cue_dir / f"{ref_stem}{ext}"
        if candidate.exists():
            return candidate
    return None

def process_cue(cue_path, dest_subdir):
    """Process a single-file CUE: split into tracks."""
    cue_data = run_cueparse(cue_path)
    if not cue_data or not cue_data.get('single_file'):
        return False

    if not cue_data.get('tracks'):
        return False

    # Find the source audio file
    if not cue_data.get('files'):
        return False

    source_audio = find_audio_for_cue(cue_path.parent, cue_data['files'][0])
    if not source_audio:
        print(f"  [Error] Audio file not found for CUE")
        return False

    bitrate = get_bitrate(source_audio.suffix)
    if not bitrate:
        return False

    os.makedirs(dest_subdir, exist_ok=True)
    total = len(cue_data['tracks'])

    for track in cue_data['tracks']:
        num = track.get('number', '00')
        title = track.get('title', f'Track {num}')
        safe_title = sanitize_filename(title)
        out_name = f"{num} - {safe_title}.opus"
        out_path = dest_subdir / out_name

        if out_path.exists():
            continue

        print(f"    [{num}/{total}] {title}")

        metadata = {
            'title': title,
            'artist': track.get('artist', ''),
            'album': cue_data.get('album', ''),
            'track': f"{num}/{total}",
            'date': cue_data.get('date', ''),
            'genre': cue_data.get('genre', ''),
            'disc': cue_data.get('disc', ''),
        }

        start = track.get('start', 0)
        duration = track.get('duration')

        if run_opusencode(source_audio, out_path, bitrate, start, duration, metadata):
            run_covercp(source_audio, out_path)
            run_coverfix(out_path)

    return True

def convert_directory(source_dir):
    """Convert all audio files in a directory tree."""
    source_dir = Path(source_dir).resolve()

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Error: Invalid directory: {source_dir}")
        return

    print(f"Source: {source_dir}")
    print(f"Target: {DEST_DIR}")
    print("-" * 50)

    # First pass: identify CUE-referenced files
    cue_sources = set()

    for cue_path in source_dir.rglob("*.cue"):
        cue_data = run_cueparse(cue_path)
        if not cue_data or not cue_data.get('single_file'):
            continue

        for ref_file in cue_data.get('files', []):
            audio_path = find_audio_for_cue(cue_path.parent, ref_file)
            if audio_path:
                cue_sources.add(audio_path.resolve())

    # Second pass: process files
    for root, _, files in os.walk(source_dir):
        root = Path(root)

        # Process CUE files
        for filename in files:
            if filename.lower().endswith('.cue'):
                cue_path = root / filename
                relative = cue_path.relative_to(source_dir.parent)
                dest_subdir = DEST_DIR / relative.parent

                cue_data = run_cueparse(cue_path)
                if cue_data and cue_data.get('single_file'):
                    print(f"[CUE] {relative}")
                    process_cue(cue_path, dest_subdir)

        # Process standalone audio files
        for filename in files:
            source_path = root / filename
            bitrate = get_bitrate(source_path.suffix)
            if not bitrate:
                continue

            # Skip if this file is handled by a CUE
            if source_path.resolve() in cue_sources:
                continue

            relative = source_path.relative_to(source_dir.parent)
            dest_path = DEST_DIR / relative.with_suffix('.opus')

            if dest_path.exists():
                continue

            print(f"[{bitrate}] {relative}")
            os.makedirs(dest_path.parent, exist_ok=True)

            if run_opusencode(source_path, dest_path, bitrate):
                run_covercp(source_path, dest_path)
                run_coverfix(dest_path)

    print("-" * 50)

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <source_dir> [source_dir2 ...]")
        print(f"\nDestination: {DEST_DIR}")
        print("\nHelper scripts required in same directory:")
        print("  - opusencode.py  (FFmpeg wrapper)")
        print("  - cueparse.py    (CUE parser)")
        print("  - covercp.py     (Cover copier)")
        print("  - coverfix.py    (Cover refresher)")
        sys.exit(1)

    # Expand globs and deduplicate
    source_dirs = []
    seen = set()

    for arg in sys.argv[1:]:
        for path in (glob.glob(arg) or [arg]):
            resolved = str(Path(path).resolve())
            if resolved not in seen:
                seen.add(resolved)
                source_dirs.append(path)

    print(f"Processing {len(source_dirs)} directory(s)...")
    print("=" * 50)

    for source_dir in source_dirs:
        convert_directory(source_dir)
        print()

    print("=" * 50)
    print("Done.")

if __name__ == "__main__":
    main()
