# WTC — Music Television

An MTV-inspired, always-on music video channel for the browser. No build step.

```bash
cd wtc && python3 -m http.server 8000   # then open http://localhost:8000
```

- **Power on** screen (browsers need a click before audio can play), then continuous shuffled playback
- **6 channels** (Hits, Rock, Hip-Hop, 80s, 90s/00s, Now) with static between channels and a station ident
- **VJ lower-thirds**: artist / song / year when a video starts, "Up next" before it ends
- **Channel guide** with "Now playing"
- Keys: ←/→ or ↑/↓ channel · 1–6 jump · N skip · M mute · G guide · F fullscreen · Space pause
- Videos play through the official YouTube embedded player; blocked/removed videos are skipped automatically

Edit `channels.js` to change the lineup (`[youtubeId, artist, title, year]`).
