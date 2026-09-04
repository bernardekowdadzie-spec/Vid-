# Javis — personal financial-regulator job assistant

A local, voice-controlled assistant that:

1. Scans the **Financial Conduct Authority (FCA)** and **Bank of England (BoE)**
   careers pages for open roles.
2. Scores each role against your skills profile.
3. Uses Claude (Anthropic API) to tailor your CV/cover note for the best matches.
4. Wakes up and shuts down on your voice ("Jarvis, wake up" / "Jarvis, go to
   sleep").
5. Logs every application you submit, and produces a report every two weeks
   summarising what you applied to, match quality, and outcomes.

## Why this runs locally, not in the cloud

Voice wake/sleep needs a live microphone and speaker on the machine you're
sitting at, and it needs to run continuously in the background. That's not
something an ephemeral cloud coding session can provide. This project is a
Python app you install and run on your own laptop/desktop (Windows, macOS,
or Linux). The job-scan and CV-tailoring logic also works fine as one-off
commands if you'd rather trigger it manually or from a scheduled task
instead of full-time voice listening.

## Important limitation — scraper selectors are unverified

The sandbox this project was built in has network egress blocked to
`fca.org.uk` and `bankofengland.co.uk`, so the CSS selectors in
`config/config.example.yaml` are **best-effort placeholders**, not
confirmed against the live markup. Career sites also restructure their HTML
periodically. Before relying on the scan:

```bash
python main.py inspect fca
python main.py inspect boe
```

This fetches the real listings page, saves the raw HTML to `output/`, and
prints every link that looks like a job posting (href containing "job" or
"vacan..."), so you can quickly confirm or correct the selectors in
`config.yaml`. If a site instead loads jobs via a JSON API (common on sites
built with Oleeo, Workday, SuccessFactors, etc.), the inspect command also
flags any embedded `<script type="application/json">` blocks so you can
switch to hitting that API directly instead of scraping HTML.

## Setup

```bash
cd jarvis-assistant
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp config/config.example.yaml config/config.yaml
cp data/skills_profile.example.yaml data/skills_profile.yaml
cp data/base_cv.example.md data/base_cv.md
cp .env.example .env             # add your ANTHROPIC_API_KEY
```

Edit `data/skills_profile.yaml` with your real skills, seniority, locations
and exclusions, and replace `data/base_cv.md` with your actual CV in
Markdown. Edit `config/config.yaml` after running `inspect` to fix selectors.

### Microphone dependencies (PyAudio)

`SpeechRecognition` needs PyAudio, which needs the system PortAudio library:

- macOS: `brew install portaudio` then `pip install pyaudio`
- Debian/Ubuntu: `sudo apt install portaudio19-dev` then `pip install pyaudio`
- Windows: `pip install pyaudio` (wheels are usually prebuilt); if that
  fails, `pip install pipwin && pipwin install pyaudio`

## Usage

```bash
# Full voice loop: listens for "Jarvis, wake up", runs the morning job
# scan on wake, takes voice commands, and listens for "Jarvis, go to sleep".
python main.py listen

# One-off runs, no mic needed - useful for testing or cron:
python main.py scan                 # scan FCA + BoE, print/save top matches
python main.py tailor <job-link>     # generate a tailored CV for one job
python main.py analyze               # biweekly application analysis, on demand
python main.py log-application \
    --title "Senior Compliance Analyst" --company "FCA" \
    --source fca --link "https://..." --match-score 0.8
```

### Voice commands once awake

| You say | Javis does |
|---|---|
| "Jarvis, wake up" | Greets you, runs the morning scan, reads out top matches |
| "scan jobs" | Re-runs the FCA/BoE scan |
| "tailor number one" / "tailor number two" ... | Generates a tailored CV for that match from the last scan |
| "read applications" | Reads back a summary of applications in the last 14 days |
| "Jarvis, go to sleep" / "goodnight Jarvis" | Reads a short wrap-up, then stops listening for commands (still listens for the wake phrase) |

Speech recognition defaults to the free Google Web Speech API via the
`SpeechRecognition` library, which sends short audio clips to Google's
servers to transcribe — fine for most personal use, but if you'd rather stay
fully offline, swap in `vosk` (see comments in `jarvis/voice.py`).

## Running it every morning / every night automatically

`python main.py listen` is a long-running process. To have it start when
you sit down and voice-control it from there, run it as a background
service that autostarts. See `SETUP_SCHEDULING.md` for systemd (Linux),
launchd (macOS), and Task Scheduler (Windows) examples, plus how to wire
the biweekly analysis into cron/Task Scheduler if you'd rather it run
unattended than be triggered by voice.

## Tracking submitted applications

There's no scraper for "did I actually apply" — that lives only in your
head or your inbox. This project logs applications to
`data/applications.json` in one of two ways:

1. **Voice/CLI**: say "log application" while awake, or run
   `python main.py log-application ...` after you submit one.
2. **Manual edit**: `data/applications.json` is plain JSON, editable by hand.

If you'd rather have applications detected automatically from confirmation
emails, that's a natural follow-up (e.g. via a Gmail integration run
periodically) but is out of scope for this first version — ask your
Claude session to add it once you've decided which inbox/labels to use.

## Project layout

```
jarvis-assistant/
  config/config.example.yaml     # copy to config.yaml
  data/
    skills_profile.example.yaml  # copy to skills_profile.yaml
    base_cv.example.md           # copy to base_cv.md
    applications.json            # application log (created on first run)
  jarvis/
    config.py                    # loads config/skills/CV
    matcher.py                   # keyword-based job/skill scoring
    cv_tailor.py                 # Claude-based CV tailoring
    applications.py              # application log read/write
    analysis.py                  # biweekly report generation
    voice.py                     # wake/sleep voice loop
    scheduler.py                 # orchestrates scan / tailor / analyze
    scrapers/
      base.py                    # generic HTML scraper
      fca.py, boe.py             # site-specific scrapers
      inspect.py                 # page-structure inspection helper
  main.py                        # CLI entrypoint
  tests/                         # pytest unit tests
  SETUP_SCHEDULING.md
```
