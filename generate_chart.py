"""
Auto-generate a Clone Hero .chart file from an audio file.
Uses librosa harmonic source separation to focus on guitar/melodic content,
with pitch-based fret assignment for more musical note placement.
"""

import glob
import os
import re

import librosa
import numpy as np
from moviepy import VideoFileClip

SONGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "songs")

RESOLUTION = 192  # ticks per quarter note (Clone Hero standard)


def detect_bpm_and_beats(y, sr):
    """Detect tempo and beat positions."""
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    if hasattr(tempo, '__len__'):
        tempo = float(tempo[0])
    return tempo, beat_times


def detect_onsets_harmonic(y, sr):
    """Detect note onsets from the harmonic (non-percussive) component."""
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    onset_frames = librosa.onset.onset_detect(
        y=y_harmonic, sr=sr, backtrack=True,
        delta=0.05, wait=3,
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    return onset_times, y_harmonic


def get_chroma_at_times(y, sr, times):
    """Get full chroma vectors and top pitch at each onset time."""
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_times = librosa.times_like(chroma, sr=sr)

    pitches = []
    chroma_vectors = []
    for t in times:
        idx = np.argmin(np.abs(chroma_times - t))
        vec = chroma[:, idx]
        pitch_class = np.argmax(vec)
        pitches.append(pitch_class)
        chroma_vectors.append(vec)
    return pitches, chroma_vectors


def assign_frets_by_pitch(pitches, num_frets=5):
    """Map pitch classes (0-11) to fret numbers (0 to num_frets-1)."""
    frets = []
    for p in pitches:
        fret = int(p * num_frets / 12)
        frets.append(min(fret, num_frets - 1))
    return frets


def detect_chords(chroma_vectors, num_frets=5, threshold=0.6):
    """
    Detect chords by finding frames where multiple pitch classes are active.
    Returns list of fret lists — single fret for normal notes, multiple for chords.
    """
    chord_frets = []
    for vec in chroma_vectors:
        if vec.max() == 0:
            chord_frets.append([0])
            continue
        normalized = vec / vec.max()
        active = np.where(normalized >= threshold)[0]
        frets = sorted(set(
            min(int(p * num_frets / 12), num_frets - 1) for p in active
        ))
        # Cap at 3 simultaneous frets max
        chord_frets.append(frets[:3])
    return chord_frets


def compute_sustain_durations(onset_times, bpm, min_gap_for_sustain=0.3):
    """
    Compute sustain duration (in ticks) for each note.
    A note gets sustain if the gap to the next note is large enough.
    Sustain length = gap minus a small release buffer, clamped to min 1/8 note.
    """
    durations = []
    eighth_note_ticks = RESOLUTION // 2
    for i, t in enumerate(onset_times):
        if i < len(onset_times) - 1:
            gap = onset_times[i + 1] - t
        else:
            gap = 1.0  # last note gets some sustain

        if gap >= min_gap_for_sustain:
            # Sustain for most of the gap, leave a small release
            sustain_sec = gap * 0.75
            sustain_ticks = time_to_tick(sustain_sec, bpm)
            durations.append(max(sustain_ticks, eighth_note_ticks))
        else:
            durations.append(0)
    return durations


def time_to_tick(time_sec, bpm, resolution=RESOLUTION):
    """Convert time in seconds to chart ticks."""
    beats_per_sec = bpm / 60.0
    beat_position = time_sec * beats_per_sec
    return int(round(beat_position * resolution))


def generate_star_power(beat_times, bpm, sp_every_bars=8, sp_length_bars=2):
    """
    Place Star Power phrases every sp_every_bars bars, each lasting sp_length_bars bars.
    Returns list of (tick, duration_ticks) tuples.
    """
    beats_per_bar = 4
    ticks_per_bar = RESOLUTION * beats_per_bar
    sp_duration = ticks_per_bar * sp_length_bars

    # Total song length in bars
    if len(beat_times) < 2:
        return []
    total_bars = int(len(beat_times) / beats_per_bar)

    phrases = []
    bar = 4  # start after 4 bars intro
    while bar + sp_length_bars <= total_bars:
        start_tick = bar * ticks_per_bar
        phrases.append((start_tick, sp_duration))
        bar += sp_every_bars

    return phrases


def generate_chart(audio_path, output_path, song_name="Unknown", artist="Unknown"):
    """Generate a .chart file from audio."""
    print(f"Loading audio: {audio_path}")
    y, sr = librosa.load(audio_path)

    print("Detecting BPM and beats...")
    bpm, beat_times = detect_bpm_and_beats(y, sr)
    print(f"  Detected BPM: {bpm:.1f}")

    # Generate Star Power phrases
    sp_phrases = generate_star_power(beat_times, bpm)
    print(f"  Star Power phrases: {len(sp_phrases)}")

    print("Separating harmonic content and detecting onsets...")
    onset_times, y_harmonic = detect_onsets_harmonic(y, sr)
    print(f"  Found {len(onset_times)} harmonic onsets")

    # Filter onsets that are too close together (min 0.05s for expert)
    filtered_onsets = [onset_times[0]]
    for t in onset_times[1:]:
        if t - filtered_onsets[-1] >= 0.05:
            filtered_onsets.append(t)
    onset_times = np.array(filtered_onsets)
    print(f"  After filtering: {len(onset_times)} notes")

    # Get pitch and chord data from harmonic content
    print("Analyzing pitch and chords...")
    pitches, chroma_vectors = get_chroma_at_times(y_harmonic, sr, onset_times)
    expert_frets = assign_frets_by_pitch(pitches, num_frets=5)
    expert_chords = detect_chords(chroma_vectors, num_frets=5, threshold=0.6)
    expert_sustains = compute_sustain_durations(onset_times, bpm, min_gap_for_sustain=0.25)

    # Build chart file
    lines = []

    # Song section
    lines.append("[Song]")
    lines.append("{")
    lines.append(f'  Name = "{song_name}"')
    lines.append(f'  Artist = "{artist}"')
    lines.append(f"  Offset = 0")
    lines.append(f"  Resolution = {RESOLUTION}")
    lines.append(f'  Player2 = "bass"')
    lines.append(f'  Difficulty = 0')
    lines.append(f'  PreviewStart = 0')
    lines.append(f'  PreviewEnd = 0')
    lines.append(f'  Genre = "rock"')
    lines.append(f'  MediaType = "cd"')
    lines.append(f'  MusicStream = "song.ogg"')
    lines.append("}")

    # Sync track (BPM markers)
    lines.append("[SyncTrack]")
    lines.append("{")
    bpm_value = int(round(bpm * 1000))
    lines.append(f"  0 = TS 4")
    lines.append(f"  0 = B {bpm_value}")
    lines.append("}")

    # Events section
    lines.append("[Events]")
    lines.append("{")
    lines.append("}")

    # Hard: harmonic onsets, wider gap (0.1s), chords on strong beats, some sustains
    hard_indices = [0]
    for i in range(1, len(onset_times)):
        if onset_times[i] - onset_times[hard_indices[-1]] >= 0.1:
            hard_indices.append(i)
    hard_times = onset_times[hard_indices]
    hard_pitches, hard_chroma = get_chroma_at_times(y_harmonic, sr, hard_times)
    hard_frets = assign_frets_by_pitch(hard_pitches, num_frets=5)
    hard_chords = detect_chords(hard_chroma, num_frets=5, threshold=0.7)
    hard_sustains = compute_sustain_durations(hard_times, bpm, min_gap_for_sustain=0.35)

    # Medium: wider gap (0.2s), 4 frets, sustains but no chords
    medium_indices = [0]
    for i in range(1, len(onset_times)):
        if onset_times[i] - onset_times[medium_indices[-1]] >= 0.2:
            medium_indices.append(i)
    medium_times = onset_times[medium_indices]
    medium_pitches, _ = get_chroma_at_times(y_harmonic, sr, medium_times)
    medium_frets = assign_frets_by_pitch(medium_pitches, num_frets=4)
    medium_sustains = compute_sustain_durations(medium_times, bpm, min_gap_for_sustain=0.4)

    # Easy: beat-aligned only, 3 frets, sustains, no chords
    easy_times = beat_times[::2]
    easy_pitches, _ = get_chroma_at_times(y_harmonic, sr, easy_times)
    easy_frets = assign_frets_by_pitch(easy_pitches, num_frets=3)
    easy_sustains = compute_sustain_durations(easy_times, bpm, min_gap_for_sustain=0.5)

    def write_sp(lines):
        for sp_tick, sp_dur in sp_phrases:
            lines.append(f"  {sp_tick} = S 2 {sp_dur}")

    # Write Expert — chords + sustains + star power
    lines.append("[ExpertSingle]")
    lines.append("{")
    for i, t in enumerate(onset_times):
        tick = time_to_tick(t, bpm)
        dur = expert_sustains[i]
        for fret in expert_chords[i]:
            lines.append(f"  {tick} = N {fret} {dur}")
    write_sp(lines)
    lines.append("}")

    # Write Hard — chords (less aggressive) + sustains + star power
    lines.append("[HardSingle]")
    lines.append("{")
    for i, t in enumerate(hard_times):
        tick = time_to_tick(t, bpm)
        dur = hard_sustains[i]
        for fret in hard_chords[i]:
            lines.append(f"  {tick} = N {fret} {dur}")
    write_sp(lines)
    lines.append("}")

    # Write Medium — single notes + sustains + star power
    lines.append("[MediumSingle]")
    lines.append("{")
    for i, t in enumerate(medium_times):
        tick = time_to_tick(t, bpm)
        dur = medium_sustains[i]
        lines.append(f"  {tick} = N {medium_frets[i]} {dur}")
    write_sp(lines)
    lines.append("}")

    # Write Easy — single notes + sustains + star power
    lines.append("[EasySingle]")
    lines.append("{")
    for i, t in enumerate(easy_times):
        tick = time_to_tick(t, bpm)
        dur = easy_sustains[i]
        lines.append(f"  {tick} = N {easy_frets[i]} {dur}")
    write_sp(lines)
    lines.append("}")

    chart_content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(chart_content)

    print(f"Chart saved to: {output_path}")
    print(f"  Difficulties: Expert ({len(onset_times)} notes), "
          f"Hard ({len(hard_times)}), Medium ({len(medium_times)}), "
          f"Easy ({len(easy_times)})")
    return bpm


def generate_song_ini(output_dir, song_name, artist, bpm):
    """Generate song.ini metadata file."""
    ini_path = os.path.join(output_dir, "song.ini")
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write("[song]\n")
        f.write(f"name = {song_name}\n")
        f.write(f"artist = {artist}\n")
        f.write(f"charter = AutoGenerated\n")
        f.write(f"diff_guitar = -1\n")
        f.write(f"preview_start_time = 0\n")
    print(f"song.ini saved to: {ini_path}")


def extract_audio(mp4_path, output_path):
    """Extract audio from an mp4 file to ogg."""
    print(f"  Extracting audio from video...")
    video = VideoFileClip(mp4_path)
    video.audio.write_audiofile(output_path, codec="libvorbis", logger=None)
    video.close()


def convert_video_to_webm(mp4_path, output_path):
    """Convert mp4 to webm for Clone Hero background video compatibility."""
    print(f"  Converting video to webm...")
    video = VideoFileClip(mp4_path)
    video.write_videofile(output_path, codec="libvpx", audio_codec="libvorbis", logger=None)
    video.close()


def parse_song_info(filename):
    """Extract song name and artist from the mp4 filename."""
    name = os.path.splitext(filename)[0]
    name = re.sub(r"\s*\([\d]+p[^)]*\)\s*$", "", name)
    name = re.sub(r"\s*\[[\d]+p[^]]*\]\s*$", "", name)

    if " - " in name:
        parts = name.split(" - ", 1)
        artist = parts[0].strip()
        song_name = parts[1].strip()
    else:
        artist = "Unknown"
        song_name = name.strip()

    return song_name, artist


def process_song_folder(song_dir):
    """Process a single song folder: extract audio, generate chart, convert video."""
    mp4_files = glob.glob(os.path.join(song_dir, "*.mp4"))
    if not mp4_files:
        return False

    audio_path = os.path.join(song_dir, "song.ogg")
    chart_path = os.path.join(song_dir, "notes.chart")
    webm_path = os.path.join(song_dir, "video.webm")

    # Skip if already processed
    if os.path.exists(audio_path) and os.path.exists(chart_path):
        print(f"  Already processed, skipping.")
        return True

    mp4_path = mp4_files[0]
    song_name, artist = parse_song_info(os.path.basename(mp4_path))
    print(f"  Song: {song_name}")
    print(f"  Artist: {artist}")

    # Extract audio if needed
    if not os.path.exists(audio_path):
        extract_audio(mp4_path, audio_path)

    # Convert video to webm if needed
    if not os.path.exists(webm_path):
        convert_video_to_webm(mp4_path, webm_path)

    # Generate chart
    bpm = generate_chart(audio_path, chart_path, song_name, artist)
    generate_song_ini(song_dir, song_name, artist, bpm)
    return True


if __name__ == "__main__":
    processed = 0
    skipped = 0

    for name in sorted(os.listdir(SONGS_DIR)):
        song_dir = os.path.join(SONGS_DIR, name)
        if not os.path.isdir(song_dir) or name.startswith("."):
            continue

        mp4_files = glob.glob(os.path.join(song_dir, "*.mp4"))
        if not mp4_files:
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {name}")
        print(f"{'='*60}")

        if process_song_folder(song_dir):
            processed += 1
        else:
            skipped += 1

    print(f"\n{'='*60}")
    print(f"Done! Processed {processed} song(s), skipped {skipped}.")
    print(f"Run 'python add_songs.py' to copy them to Clone Hero.")
