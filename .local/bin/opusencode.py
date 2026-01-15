#!/usr/bin/env python3
"""
opusencode - Encode audio to Opus format.

Usage:
    opusencode.py -i INPUT -o OUTPUT -b BITRATE [options]

Options:
    -i, --input     Input audio file
    -o, --output    Output opus file
    -b, --bitrate   Target bitrate (e.g., 96k, 192k)
    -s, --start     Start time in seconds (for segment extraction)
    -d, --duration  Duration in seconds (for segment extraction)
    -m, --meta      Metadata as key=value (can be repeated)

Example:
    opusencode.py -i song.flac -o song.opus -b 96k
    opusencode.py -i album.flac -o track01.opus -b 96k -s 0 -d 180 -m title="Song"
"""

import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description='Encode audio to Opus')
    parser.add_argument('-i', '--input', required=True, help='Input file')
    parser.add_argument('-o', '--output', required=True, help='Output file')
    parser.add_argument('-b', '--bitrate', required=True, help='Bitrate (e.g., 96k)')
    parser.add_argument('-s', '--start', type=float, help='Start time (seconds)')
    parser.add_argument('-d', '--duration', type=float, help='Duration (seconds)')
    parser.add_argument('-m', '--meta', action='append', default=[], help='Metadata key=value')

    args = parser.parse_args()

    cmd = [
        'ffmpeg',
        '-y',
        '-nostdin',
        '-loglevel', 'error',
    ]

    # Seek before input for efficiency
    if args.start is not None:
        cmd.extend(['-ss', f"{args.start:.6f}"])

    cmd.extend(['-i', args.input])

    # Duration after input
    if args.duration is not None:
        cmd.extend(['-t', f"{args.duration:.6f}"])

    cmd.extend([
        '-map', '0:a',
        '-vn',
        '-c:a', 'libopus',
        '-b:a', args.bitrate,
        '-vbr', 'on',
        '-map_metadata', '0',
    ])

    # Add metadata overrides
    for meta in args.meta:
        cmd.extend(['-metadata', meta])

    cmd.append(args.output)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: ffmpeg failed with code {e.returncode}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
