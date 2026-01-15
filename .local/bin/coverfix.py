#!/usr/bin/env python3
"""
coverfix - Refresh album cover in Opus files.

Usage:
    coverfix.py                     (Recursively process current directory)
    coverfix.py <dir>               (Recursively process specific directory)
    coverfix.py <file.opus> ...     (Process specific files)

Forces cover type to Front Cover (type 3) and performs a refresh cycle
(delete + re-add) which fixes display issues in many players.
"""

import sys
import os
import base64
import glob

try:
    from mutagen.oggopus import OggOpus
    from mutagen.flac import Picture
except ImportError:
    print("Error: mutagen library required. Run: pip install mutagen", file=sys.stderr)
    sys.exit(1)

def refresh_cover(filepath):
    """Refresh cover in a single Opus file. Returns status string."""
    try:
        audio = OggOpus(filepath)

        if 'metadata_block_picture' not in audio.tags:
            return 'skip'

        b64_pictures = audio.tags['metadata_block_picture']
        new_pictures = []
        modified = False

        for b64_data in b64_pictures:
            raw_data = base64.b64decode(b64_data)
            pic = Picture(raw_data)

            # Force type 3 (Front Cover)
            if pic.type != 3:
                pic.type = 3
                pic.desc = 'Front Cover'
                modified = True

            new_b64 = base64.b64encode(pic.write()).decode('ascii')
            new_pictures.append(new_b64)

        # The refresh cycle: delete and re-add
        del audio.tags['metadata_block_picture']
        audio.save()

        audio.tags['metadata_block_picture'] = new_pictures
        audio.save()

        return 'fixed' if modified else 'refreshed'

    except Exception as e:
        return f'error: {e}'

def main():
    targets = sys.argv[1:]

    # If no arguments, recurse current directory
    if not targets:
        targets = ['.']

    files = []

    for target in targets:
        # If target is a directory, recurse for .opus files
        if os.path.isdir(target):
            # Python 3.5+ recursive glob
            search_pattern = os.path.join(target, '**', '*.opus')
            found = glob.glob(search_pattern, recursive=True)
            files.extend(found)
        else:
            # Otherwise treat as file path or glob pattern (Legacy/Opusconv mode)
            expanded = glob.glob(target)
            files.extend(expanded if expanded else [target])

    # Remove duplicates and sort
    files = sorted(list(set(files)))

    if not files:
        print("No Opus files found.")
        sys.exit(0)

    for filepath in files:
        # Skip directories if they accidentally got into the list via glob
        if os.path.isdir(filepath):
            continue

        status = refresh_cover(filepath)

        if status == 'skip':
            print(f"[Skip] No cover: {filepath}")
        elif status == 'fixed':
            print(f"[Fixed] Type corrected & refreshed: {filepath}")
        elif status == 'refreshed':
            print(f"[OK] Refreshed: {filepath}")
        else:
            print(f"[Error] {filepath}: {status}")

if __name__ == "__main__":
    main()
