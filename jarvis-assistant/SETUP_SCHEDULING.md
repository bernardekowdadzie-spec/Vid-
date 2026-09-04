# Running Javis unattended / on autostart

## Option A: voice-controlled, running whenever your machine is on

Run `python main.py listen` as a background service that starts on login,
so you can just say the wake/sleep phrases without opening a terminal.

### Linux (systemd user service)

Create `~/.config/systemd/user/javis.service`:

```ini
[Unit]
Description=Javis voice job assistant

[Service]
WorkingDirectory=/absolute/path/to/jarvis-assistant
ExecStart=/absolute/path/to/jarvis-assistant/.venv/bin/python main.py listen
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now javis.service
```

### macOS (launchd)

Create `~/Library/LaunchAgents/com.javis.assistant.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.javis.assistant</string>
  <key>ProgramArguments</key>
  <array>
    <string>/absolute/path/to/jarvis-assistant/.venv/bin/python</string>
    <string>main.py</string>
    <string>listen</string>
  </array>
  <key>WorkingDirectory</key><string>/absolute/path/to/jarvis-assistant</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.javis.assistant.plist
```

### Windows (Task Scheduler)

Task Scheduler → Create Task → Trigger: "At log on" → Action: Start a
program → Program: `C:\path\to\jarvis-assistant\.venv\Scripts\python.exe`,
Arguments: `main.py listen`, Start in:
`C:\path\to\jarvis-assistant`.

## Option B: unattended biweekly analysis (no voice needed)

If you don't want Javis running full-time, you can still get the biweekly
report automatically by scheduling `python main.py analyze`.

### Linux/macOS (cron)

```
crontab -e
# Runs every other Monday at 08:00
0 8 * * 1 [ $(( $(date +\%s) / 604800 \% 2 )) -eq 0 ] && cd /absolute/path/to/jarvis-assistant && .venv/bin/python main.py analyze
```

(cron has no native "every 2 weeks" - the snippet above runs weekly and
skips every other week via a date check; simplest alternative is to just
run it weekly and read the 2-week rolling window each time, which
`main.py analyze` already does by default.)

### Windows (Task Scheduler)

Create a task with a weekly trigger, "recur every 2 weeks", Action: run
`python.exe main.py analyze` with Start in set to the project folder.

## Getting the report/tailored CVs onto your phone or inbox

`main.py analyze` and `main.py tailor` just write files into `output/`.
If you want the biweekly report emailed to you automatically, that's a
natural extension (e.g. via Gmail) - ask your Claude session to wire that
up once you've decided which account/credentials to use.
