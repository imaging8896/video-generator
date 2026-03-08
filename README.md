# video-generator

Automatically generate a YouTube Shorts video every day using **Grok AI** and publish it to YouTube.

## What it does

1. **Grok AI generates the script** — picks a trending, educational topic and writes a ≤ 120-word narration optimised for maximum engagement and full YouTube-guideline compliance.
2. **Builds a vertical MP4 video** (1080 × 1920, ≤ 60 s) from:
   - Slide images rendered with Pillow (no copyrighted assets)
   - AI-generated voiceover via gTTS
   - Video compositing with MoviePy
3. **Uploads to YouTube as Shorts** via the YouTube Data API v3 with public visibility, relevant tags, and `#Shorts` in the title.
4. **Runs automatically every day at 08:00 UTC** via GitHub Actions.

---

## Quick start

### 1. Clone & install

```bash
git clone https://github.com/imaging8896/video-generator.git
cd video-generator
pip install -r requirements.txt
```

### 2. Get a Grok AI API key

Sign up at <https://console.x.ai/> and create an API key.

### 3. Set up YouTube OAuth2 (one-time)

1. Go to <https://console.cloud.google.com/> → create a project.
2. Enable the **YouTube Data API v3**.
3. Create **OAuth 2.0 credentials** (Desktop app type) and download `client_secrets.json`.
4. Place `client_secrets.json` in the `scripts/` directory.
5. Run the setup helper:

```bash
python scripts/setup_youtube_auth.py
```

The script opens a browser for authorisation and then prints the three values you need to save as **GitHub repository secrets**.

### 4. Add GitHub Secrets

In your repository → **Settings → Secrets and variables → Actions**, add:

| Secret | Description |
|---|---|
| `XAI_API_KEY` | Your xAI / Grok API key |
| `YOUTUBE_CLIENT_ID` | From the setup script output |
| `YOUTUBE_CLIENT_SECRET` | From the setup script output |
| `YOUTUBE_REFRESH_TOKEN` | From the setup script output |

Optionally set the **repository variable** `TTS_LANGUAGE` (default: `en`) to change the narration language.

### 5. Run manually or wait for the daily schedule

The workflow runs automatically every day at **08:00 UTC**.
You can also trigger it manually: **Actions → Daily YouTube Shorts Generator → Run workflow**.

---

## Project structure

```
video-generator/
├── src/
│   ├── content_generator.py   # Grok AI script generation
│   ├── video_creator.py       # PIL + MoviePy video assembly
│   ├── youtube_uploader.py    # YouTube Data API v3 upload
│   └── main.py                # Pipeline entry point
├── scripts/
│   └── setup_youtube_auth.py  # One-time OAuth2 setup helper
├── .github/workflows/
│   └── daily_video.yml        # Daily cron workflow
├── .env.example               # Example environment variables
└── requirements.txt
```

---

## Content policy

All generated content:
- Is factual, original, and educational
- Contains no copyrighted material (no music, no trademarked content)
- Complies with [YouTube Community Guidelines](https://www.youtube.com/howyoutubeworks/policies/community-guidelines/)
- Avoids controversial, harmful, or misleading topics

The Grok AI prompt explicitly enforces these constraints on every run.

---

## License

MIT — see [LICENSE](LICENSE).
