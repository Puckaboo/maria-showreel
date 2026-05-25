# Maria showreel — rough-cut pipeline

This is a simple automated editing tool. You tell it which moments to use and it assembles them into a single video.

Output: `output/maria_showreel_roughcut.mp4`

---

## 1. Install ffmpeg

You need ffmpeg installed once. On macOS:

```bash
brew install ffmpeg
```

Check it works:

```bash
ffmpeg -version
```

---

## 2. The source videos are already here

All source videos are in `video-selection/`. The files already present are:

```text
video-selection/
  ＂Open Canvas＂ by Jlin & HIIIT [3P-A7J6Pqnc].mp4
  ＂Speed Of Darkness＂ by Jlin & HIIIT [gz85boURfws].mp4
  ＂The Move Groove＂ by Jlin & HIIIT [eEGf4yjfd4E].mp4
  DDD Grand - Charity Gala - Spieren voor Spieren [KvDDFS-zNhw].mp4
  F.E.M. - Feminine Energetic Music - PROMO TRAILER 2025 [66K3YZ625c8].mp4
  Jamai Loman dirigeert Mercury Rising van Daughtrey ｜ Maestro [qeYoU-lR_-k].mp4
  Loading Dock Session #24 ｜ with upsammy [4PWvV6z4FHU].mp4
  Simone Kleinsma： VERDER - Trailer [Xo0tKfQNhHs].mp4
  Trailer Nieuw Babylon 9x13 [yiUM3N-7aqk].mp4
  Trailer Superball, Lollipop & Mr. Classic van Oorkaan met HIIIT [6mpKr-avvlY].mp4
```

The script identifies each file by the YouTube ID in brackets — the part between `[` and `]`. As long as that ID stays in the filename, you can rename the file however you like.

To add a new source video, download it with yt-dlp and drop it in `video-selection/`.

---

## 3. Edit the cut list

Open `edit_decision_list.csv`. This is where all the editing decisions live.

Each row is one shot:

| column | meaning |
|---|---|
| `order` | position in the final edit (1 = first) |
| `section` | narrative section (intro, musicianship, energy, authority, theatrical, ending) |
| `source_id` | YouTube ID of the source video |
| `source_hint` | human-readable name of the source (for your reference only) |
| `start` | timecode where the clip starts, format `HH:MM:SS` |
| `end` | timecode where the clip ends, format `HH:MM:SS` |
| `label` | short description of what happens in this shot |
| `mute` | `no` = keep original audio, `yes` = silence this clip |

**To change a cut:** adjust `start` and `end` in the row.  
**To reorder shots:** change the `order` numbers.  
**To remove a shot:** delete the row.  
**To add a shot:** add a new row with the next order number.

### About the `mute` column

Right now all clips have `mute=no`, so the rough cut uses the original audio from each source. This is good for a first pass — you can hear what each moment sounds like in context.

Once the structure feels right, the next step is to add one continuous music bed (the Jlin/HIIIT material works well for this). When you do that:

1. Set `mute=yes` on every row in the CSV.
2. Add the music bed as a separate audio track in your video editor or ask for a script update to do it automatically.

---

## 4. Run the script

From this folder in Terminal:

```bash
python3 make_showreel.py
```

The script will:
1. Read every row in `edit_decision_list.csv`
2. Find the matching video in `video-selection/`
3. Cut out the exact moment you specified
4. Normalize everything to 1920×1080, 25 fps, H.264
5. Join all clips in order into one file

The result appears at:

```text
output/maria_showreel_roughcut.mp4
```

Individual clips are saved in `work/` so you can check any single moment without re-running everything.

---

## 5. Clean up and start fresh

To delete all generated files and run again from scratch:

```bash
bash clean.sh
```

---

## Next improvements (in order)

1. Add one continuous audio bed (Jlin/HIIIT) and set all clips to `mute=yes`.
2. Add a short fade-in at the start and fade-out at the end.
3. Add a minimal name card — just "Maria Martinez Paya", small, early.
4. Experiment with cut timing against the music beat.
