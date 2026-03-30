# Clone Hero Track Generator

Auto-generate [Clone Hero](https://clonehero.net/) custom songs from video files. Extracts audio, separates harmonic content to focus on guitar, and creates playable `.chart` files with:

- Four difficulty levels (Easy, Medium, Hard, Expert)
- Pitch-based fret assignment using chromagram analysis
- Sustained notes on longer gaps
- Chords (Expert/Hard) detected from multiple active pitches
- Star Power phrases
- Background video (converted to `.webm` for compatibility)

## Pre-made Songs

Don't want to generate your own? Download ready-to-play song packs from the [Releases](https://github.com/MatiasCiccone/misa-hero/releases) page.

1. Download the `.zip` from the latest release
2. Extract into your Clone Hero `Songs/` directory
3. Open Clone Hero, go to **Settings > General**, and hit **Scan Songs**

## Requirements

- [Clone Hero](https://clonehero.net/)
- Python 3.10+

## Setup

```bash
git clone https://github.com/MatiasCiccone/misa-hero.git misa-hero
cd misa-hero

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Usage

### 1. Add your video

Create a folder for your song inside `songs/` and place the `.mp4` inside:

```
misa-hero/
  songs/
    my-song/
      Artist - Song Title (1080p, h264).mp4
```

Name your files as `Artist - Song Title.mp4` for best metadata detection.

### 2. Generate charts

```bash
python generate_chart.py
```

The script automatically scans all subfolders in `songs/` for `.mp4` files and for each one:
- Extracts audio into `song.ogg`
- Converts video to `video.webm` for Clone Hero background playback
- Separates harmonic content (filters out drums) for guitar-focused onset detection
- Detects BPM, note onsets, pitch, and chords
- Generates `notes.chart` with four difficulties, sustains, chords, and Star Power
- Creates `song.ini` with song metadata

Already-processed folders are skipped. Delete the generated files in a song folder to re-process it.

### 3. Add songs to Clone Hero

```bash
python add_songs.py
```

This copies all ready songs into Clone Hero's Songs directory. The script auto-detects common Clone Hero install paths.

If your install is in a non-standard location:

```bash
# Using --target flag
python add_songs.py --target "/path/to/Clone Hero/Songs"

# Or using environment variable
export CLONE_HERO_SONGS="/path/to/Clone Hero/Songs"
python add_songs.py
```

Then open Clone Hero, go to **Settings > General**, and hit **Scan Songs**.

### Song folder structure

After generation, each song folder will contain:

| File | Description |
|------|-------------|
| `*.mp4` | Original video (kept for reference) |
| `song.ogg` | Extracted audio |
| `video.webm` | Background video for Clone Hero |
| `notes.chart` | Auto-generated chart |
| `song.ini` | Song metadata |
