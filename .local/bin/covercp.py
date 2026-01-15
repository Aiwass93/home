#!/usr/bin/env python3
"""
covercp - Copy album cover from source audio file to Opus file.

Usage: covercp.py <source> <dest.opus>

Extracts cover from source and embeds it into the destination Opus file.
"""

import sys
import base64

try:
    from mutagen import File
    from mutagen.flac import Picture
    from mutagen.oggopus import OggOpus
except ImportError:
    print("Error: mutagen library required. Run: pip install mutagen", file=sys.stderr)
    sys.exit(1)

def extract_cover(source_path):
    """Extract first cover image from audio file. Returns raw bytes or None."""
    try:
        audio = File(source_path)
        if audio is None:
            return None

        # FLAC/Vorbis pictures
        if hasattr(audio, 'pictures') and audio.pictures:
            return audio.pictures[0].data

        if not hasattr(audio, 'tags') or audio.tags is None:
            return None

        # ID3 APIC (MP3, AIFF)
        for key in audio.tags.keys():
            if key.startswith('APIC:'):
                return audio.tags[key].data

        # MP4/M4A covr
        if 'covr' in audio.tags and audio.tags['covr']:
            return bytes(audio.tags['covr'][0])

        return None
    except Exception as e:
        print(f"Warning: Could not extract cover: {e}", file=sys.stderr)
        return None

def embed_cover(dest_path, image_data):
    """Embed cover image into Opus file."""
    try:
        audio = OggOpus(dest_path)

        # Create Picture block
        pic = Picture()
        pic.data = image_data
        pic.type = 3  # Front cover
        pic.desc = 'Front Cover'

        # Guess MIME type from magic bytes
        if image_data[:3] == b'\xff\xd8\xff':
            pic.mime = 'image/jpeg'
        elif image_data[:8] == b'\x89PNG\r\n\x1a\n':
            pic.mime = 'image/png'
        else:
            pic.mime = 'image/jpeg'  # Default assumption

        # Encode and embed
        encoded = base64.b64encode(pic.write()).decode('ascii')
        audio['metadata_block_picture'] = [encoded]
        audio.save()

        return True
    except Exception as e:
        print(f"Warning: Could not embed cover: {e}", file=sys.stderr)
        return False

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <source> <dest.opus>", file=sys.stderr)
        sys.exit(1)

    source = sys.argv[1]
    dest = sys.argv[2]

    cover_data = extract_cover(source)
    if cover_data is None:
        print(f"No cover found in: {source}", file=sys.stderr)
        sys.exit(0)  # Not an error, just no cover

    if embed_cover(dest, cover_data):
        print(f"Cover copied: {source} -> {dest}")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
