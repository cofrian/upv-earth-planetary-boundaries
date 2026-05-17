# UPV-EARTH Launch Video — Music Integration

## Quick Start

Your video is **180 seconds (3:00)** and needs a **cinematic, minimal startup soundtrack**.

### Step 1: Get a Music Track

Choose ONE:

#### Option A: Royalty-Free (Recommended)
- **Pexels Music** (pexels.com/music)
  - Search: "startup launch", "cinematic tech", "minimal ambient"
  - Filter: 2:50–3:00 duration
  - Download: MP3, highest quality

- **Pixabay Music** (pixabay.com/music)
  - Same search terms
  - CC0 licensed (free forever)

#### Option B: AI-Generated (Custom)
```
Prompt for Suno.com or Mubert.com:
"Minimalist cinematic startup launch music. 180 seconds.
Quiet introspective open, builds through middle, fades completely by end.
Tech, future, innovation, trust. Synth, ambient pads, subtle swells.
Perfect for product demo video."
```

#### Option C: Specific Recommendations
- **"Ambient Intro"** by Kevin MacLeod (incompetech.com) — free, perfect vibe
- **"Uplifting Technology"** by Pexels curators — minimal synth
- Search YouTube Audio Library: "tech startup", "launch"

**Pick one that:**
- Is 2:50–3:10 seconds (you need exactly 180s)
- Starts quiet (doesn't interrupt the Hook)
- Builds energy during the Features tour
- Fades to silence by "Available now"

---

### Step 2: Add to Project

```bash
# From project root:
mkdir -p launch-video/public/music

# Copy your downloaded .mp3 here:
cp ~/Downloads/your-music-track.mp3 launch-video/public/music/launch-bg.mp3
```

---

### Step 3: Update Root.tsx

Open `launch-video/src/Root.tsx` and add the Audio import:

```tsx
import {Audio, staticFile} from 'remotion';
```

Then add the audio inside the `<Series>` component (right after `<ProjectWatermark />`):

```tsx
<Series>
  <ProjectWatermark />
  <Audio src={staticFile('music/launch-bg.mp3')} />
  
  {/* Rest of Series.Sequence components... */}
</Series>
```

**Full context:**
```tsx
const LaunchVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: colors.bg}}>
      <ProjectWatermark />
      <Series>
        <Audio src={staticFile('music/launch-bg.mp3')} />
        
        <Series.Sequence durationInFrames={240}>
          <Act1Hook />
        </Series.Sequence>
        {/* ... rest of acts ... */}
      </Series>
    </AbsoluteFill>
  );
};
```

---

### Step 4: Render with Audio

```bash
cd launch-video

# Preview in browser (includes audio)
npm start

# Render final video WITH audio
npm run build -- --include-audio
```

The final MP4 will be in `out/UPV-EARTH-launch-180s.mp4`

---

## Audio Level Tuning

Music should **enhance, not dominate**. Here's the mix:

| Section | Voiceover Level | Music Level | Notes |
|---------|-----------------|-------------|-------|
| Hook (0:00–0:08) | -12dB | -24dB | Quiet entrance, music very subtle |
| Manifesto (0:08–0:20) | -12dB | -20dB | Builds slightly |
| Reveal (0:20–0:26) | -12dB | -15dB | Music swells with logo |
| Features Tour (0:26–1:34) | -12dB | -18dB | Music peaks during UMAP/Pipeline |
| Vision (1:34–1:46) | -12dB | -12dB | Music soft, reflective |
| CTA (1:46–2:00) | -12dB | -24dB → -∞dB | Music fades out completely |

**If your track needs volume adjustment:**

Create `launch-video/src/components/AudioWithGain.tsx`:

```tsx
import {Audio, staticFile} from 'remotion';

export const AudioWithGain: React.FC<{gain?: number}> = ({gain = -12}) => {
  return (
    <Audio 
      src={staticFile('music/launch-bg.mp3')}
      volume={Math.pow(10, gain / 20)} // Convert dB to linear
    />
  );
};
```

Then use it: `<AudioWithGain gain={-15} />`

---

## Troubleshooting

### Audio not playing in preview?
```bash
# Clear cache and restart
rm -rf .remotion
npm start
```

### Audio is too loud?
Lower the volume: `<Audio src={...} volume={0.5} />`
(0 = silent, 1 = full volume)

### Video renders but audio is missing?
Make sure you use `--include-audio` flag:
```bash
npm run build -- --include-audio
```

### Final file is huge (>500MB)?
Remotion embeds high-quality audio. This is normal. You can compress after:
```bash
ffmpeg -i out/UPV-EARTH-launch-180s.mp4 \
  -c:v libx264 -preset slow -crf 18 \
  -c:a aac -b:a 128k \
  UPV-EARTH-launch-final.mp4
```

---

## Music Recommendations Ranked

**✓ BEST (Startup Vibes)**
1. Pexels Audio — "Ambient Startup" by various curators
2. Custom Suno generation (5–10min wait, perfect fit)
3. Epidemic Sound — "Technology" collection

**GOOD (Free)**
4. Pixabay Music — "Minimal Synth" tag
5. Kevin MacLeod (incompetech.com) — "Ambient" category

**AVOID**
- Loud electronic (overpowers the product demo)
- Heavily compressed royalty-free (low quality)
- Copyrighted tracks (Spotify, Apple Music — illegal without license)

---

## Files Reference

```
launch-video/
├── public/music/
│   └── launch-bg.mp3          ← Your music file goes here
├── src/
│   ├── Root.tsx               ← Add <Audio /> here
│   └── scenes/
└── MUSIC_SETUP.md             ← This file
```

---

## Final Check Before Rendering

```bash
# 1. Music file exists
ls -lh launch-video/public/music/launch-bg.mp3

# 2. Root.tsx has Audio import and component
grep -n "Audio\|staticFile" launch-video/src/Root.tsx

# 3. Duration is exactly 180 seconds (your video) or slightly longer (will be trimmed)
ffprobe launch-video/public/music/launch-bg.mp3 -show_entries format=duration

# 4. Test render
npm run build -- --include-audio
```

---

## Questions?

- **Why not add music via FFmpeg after?** Remotion handles sync perfectly; post-processing risks drift
- **Can I change music after rendering?** Yes, render again with a different track
- **Does music affect video length?** No, video is still exactly 180 seconds regardless of audio

