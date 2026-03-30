"""
Copy all ready song folders from clone-hero-tracks into Clone Hero's Songs directory.
Only copies the files Clone Hero needs (song.ogg, notes.chart, song.ini, video.webm).

Set the CLONE_HERO_SONGS environment variable to override the default Songs path.
"""

import argparse
import glob
import os
import shutil

TRACKS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "songs"
)

DEFAULT_CLONE_HERO_PATHS = [
    os.path.join(os.path.expanduser("~"), "Documents", "Clone Hero", "Songs"),
    os.path.join(os.path.expanduser("~"), "OneDrive", "Documents", "Clone Hero", "Songs"),
    os.path.join(os.path.expanduser("~"), "OneDrive", "Documentos", "Clone Hero", "Songs"),
    os.path.join(os.path.expanduser("~"), ".clonehero", "Songs"),
]


def find_clone_hero_songs():
    """Auto-detect Clone Hero Songs directory."""
    env = os.environ.get("CLONE_HERO_SONGS")
    if env:
        return env
    for path in DEFAULT_CLONE_HERO_PATHS:
        if os.path.isdir(os.path.dirname(path)):
            return path
    return None

REQUIRED_FILES = ["song.ogg", "notes.chart"]
COPY_FILES = ["song.ogg", "notes.chart", "song.ini"]


def is_ready(song_dir):
    """Check if a song folder has all required files."""
    return all(os.path.exists(os.path.join(song_dir, f)) for f in REQUIRED_FILES)


def add_songs(clone_hero_songs):
    os.makedirs(clone_hero_songs, exist_ok=True)

    added = 0
    skipped = 0

    for name in os.listdir(TRACKS_DIR):
        song_dir = os.path.join(TRACKS_DIR, name)
        if not os.path.isdir(song_dir) or name.startswith("."):
            continue

        if not is_ready(song_dir):
            print(f"  SKIP (not ready): {name}")
            skipped += 1
            continue

        dest_dir = os.path.join(clone_hero_songs, name)
        if os.path.exists(dest_dir):
            print(f"  SKIP (already exists): {name}")
            skipped += 1
            continue

        os.makedirs(dest_dir, exist_ok=True)
        for filename in COPY_FILES:
            src = os.path.join(song_dir, filename)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dest_dir, filename))

        # Copy webm for background video (more compatible with Clone Hero)
        webm_path = os.path.join(song_dir, "video.webm")
        if os.path.exists(webm_path):
            shutil.copy2(webm_path, os.path.join(dest_dir, "video.webm"))

        print(f"  ADDED: {name}")
        added += 1

    print(f"\nDone! Added {added} song(s), skipped {skipped}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy songs to Clone Hero")
    parser.add_argument(
        "--target", "-t",
        help="Path to Clone Hero Songs directory (or set CLONE_HERO_SONGS env var)",
    )
    args = parser.parse_args()

    clone_hero_songs = args.target or find_clone_hero_songs()
    if not clone_hero_songs:
        print("ERROR: Could not find Clone Hero Songs directory.")
        print("Use --target /path/to/Clone\\ Hero/Songs or set CLONE_HERO_SONGS env var.")
        exit(1)

    print(f"Source:  {TRACKS_DIR}")
    print(f"Target:  {clone_hero_songs}\n")
    add_songs(clone_hero_songs)
