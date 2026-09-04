"""Local JSON-backed log of submitted applications.

This is the source of truth the biweekly analysis reads from. There's no
automatic "you applied" detection - entries are added via voice/CLI
(`log-application`) or by hand-editing the JSON file.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4


@dataclass
class Application:
    id: str
    title: str
    company: str
    source: str
    link: str
    date_applied: str  # ISO date, e.g. "2026-09-04"
    status: str = "submitted"  # submitted | interview | rejected | offer | withdrawn
    match_score: float | None = None
    notes: str = ""

    @staticmethod
    def new(
        title: str,
        company: str,
        source: str,
        link: str,
        date_applied: str | None = None,
        status: str = "submitted",
        match_score: float | None = None,
        notes: str = "",
    ) -> "Application":
        return Application(
            id=str(uuid4()),
            title=title,
            company=company,
            source=source,
            link=link,
            date_applied=date_applied or date.today().isoformat(),
            status=status,
            match_score=match_score,
            notes=notes,
        )


class ApplicationLog:
    def __init__(self, path: Path):
        self.path = path
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("[]", encoding="utf-8")

    def load(self) -> list[Application]:
        raw = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        return [Application(**item) for item in raw]

    def save(self, applications: list[Application]) -> None:
        raw = [asdict(a) for a in applications]
        self.path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def append(self, application: Application) -> None:
        applications = self.load()
        applications.append(application)
        self.save(applications)

    def in_range(self, since: date, until: date) -> list[Application]:
        out = []
        for app in self.load():
            try:
                applied = datetime.strptime(app.date_applied, "%Y-%m-%d").date()
            except ValueError:
                continue
            if since <= applied <= until:
                out.append(app)
        return out
