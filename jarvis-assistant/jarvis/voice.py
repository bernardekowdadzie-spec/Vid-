"""Voice wake/sleep loop.

Two states:
  DORMANT - only listens for the wake phrase (default: "jarvis wake up").
  AWAKE   - takes spoken commands until the sleep phrase is heard.

Uses SpeechRecognition (Google's free web API by default) for STT and
pyttsx3 (fully offline) for TTS. To go fully offline for STT too, install
`vosk` and swap `recognizer.recognize_google(audio)` below for a Vosk-based
recognizer - left as free-form STT here to keep first-run setup simple.
"""

from __future__ import annotations

import speech_recognition as sr
import pyttsx3

from jarvis.config import AppConfig
from jarvis.matcher import MatchResult
from jarvis.scheduler import run_analysis, run_scan, run_tailor


class Javis:
    def __init__(self, config: AppConfig):
        self.config = config
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", config.raw.get("voice", {}).get("tts_rate", 175))
        self.last_matches: list[MatchResult] = []
        self.awake = False

    def say(self, text: str) -> None:
        print(f"{self.config.assistant_name}: {text}")
        self.tts.say(text)
        self.tts.runAndWait()

    def _listen_once(self) -> str | None:
        voice_cfg = self.config.raw.get("voice", {})
        timeout = voice_cfg.get("listen_timeout_seconds", 8)
        phrase_limit = voice_cfg.get("phrase_time_limit_seconds", 6)
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            except sr.WaitTimeoutError:
                return None
        try:
            return self.recognizer.recognize_google(audio).lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            print(f"[warning] speech recognition service error: {exc}")
            return None

    def _wake_up(self) -> None:
        self.awake = True
        self.say(f"Good morning. I'm {self.config.assistant_name}, running your FCA and Bank of England job scan now.")
        try:
            self.last_matches = run_scan(self.config)
        except Exception as exc:  # scan failures shouldn't kill the voice loop
            self.say("The job scan hit an error, check the terminal for details.")
            print(f"[error] scan failed: {exc}")
            return

        if not self.last_matches:
            self.say("No new roles matched your skills profile above the minimum score today.")
            return

        self.say(f"I found {len(self.last_matches)} matching roles. Here are the top ones.")
        for i, match in enumerate(self.last_matches[:5], start=1):
            self.say(f"Number {i}: {match.posting.title}, {match.posting.source.upper()}, {match.score:.0%} match.")
        self.say("Say 'tailor number' followed by a number to generate a tailored CV for one of these.")

    def _go_to_sleep(self) -> None:
        self.say("Wrapping up. Remember to log any applications you submit. Goodnight.")
        self.awake = False

    def _handle_command(self, text: str) -> None:
        if "scan" in text:
            self.say("Re-running the job scan.")
            self.last_matches = run_scan(self.config)
            self.say(f"Found {len(self.last_matches)} matches." if self.last_matches else "No matches found.")
            return

        if "tailor" in text:
            index = self._extract_number(text)
            if index is None or index < 1 or index > len(self.last_matches):
                self.say("Say 'tailor number' followed by a valid result number from the last scan.")
                return
            match = self.last_matches[index - 1]
            self.say(f"Tailoring your CV for {match.posting.title}. This may take a moment.")
            try:
                out_path = run_tailor(self.config, match)
                self.say(f"Done. Saved to {out_path.name}.")
            except Exception as exc:
                self.say("CV tailoring failed, check the terminal for details.")
                print(f"[error] tailoring failed: {exc}")
            return

        if "read applications" in text or "applications" in text:
            self.say("Generating your application analysis.")
            try:
                out_path = run_analysis(self.config)
                self.say(f"Analysis saved to {out_path.name}. Check it for the full breakdown.")
            except Exception as exc:
                self.say("Analysis failed, check the terminal for details.")
                print(f"[error] analysis failed: {exc}")
            return

        self.say("I didn't catch a command I recognize. Try 'scan jobs', 'tailor number one', or 'read applications'.")

    @staticmethod
    def _extract_number(text: str) -> int | None:
        words_to_num = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        }
        for word, num in words_to_num.items():
            if word in text:
                return num
        for token in text.split():
            if token.isdigit():
                return int(token)
        return None

    def run_forever(self) -> None:
        wake_phrase = self.config.wake_phrase
        sleep_phrase = self.config.sleep_phrase
        require_wake_each_time = self.config.raw.get("voice", {}).get("require_wake_word_each_time", False)

        print(f"{self.config.assistant_name} is listening for the wake phrase: '{wake_phrase}'")
        try:
            while True:
                text = self._listen_once()
                if not text:
                    continue
                print(f"[heard] {text}")

                if not self.awake:
                    if wake_phrase in text:
                        self._wake_up()
                    continue

                if sleep_phrase in text or "goodnight jarvis" in text:
                    self._go_to_sleep()
                    continue

                if require_wake_each_time and wake_phrase not in text:
                    continue

                self._handle_command(text)
        except KeyboardInterrupt:
            print("\nStopped.")
