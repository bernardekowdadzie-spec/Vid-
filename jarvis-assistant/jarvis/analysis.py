"""Biweekly analysis of submitted applications.

Pure offline computation over data/applications.json - no API key needed.
If ANTHROPIC_API_KEY is set, also asks Claude to write a short narrative
summary on top of the computed stats; otherwise falls back to a templated
summary.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from jarvis.applications import Application, ApplicationLog
from jarvis.config import AppConfig


@dataclass
class PeriodStats:
    since: date
    until: date
    total: int
    by_status: Counter
    by_source: Counter
    average_match_score: float | None
    applications: list[Application]


def compute_period_stats(log: ApplicationLog, since: date, until: date) -> PeriodStats:
    applications = log.in_range(since, until)
    by_status = Counter(a.status for a in applications)
    by_source = Counter(a.source for a in applications)
    scores = [a.match_score for a in applications if a.match_score is not None]
    avg_score = round(sum(scores) / len(scores), 3) if scores else None
    return PeriodStats(
        since=since,
        until=until,
        total=len(applications),
        by_status=by_status,
        by_source=by_source,
        average_match_score=avg_score,
        applications=applications,
    )


def _templated_summary(stats: PeriodStats) -> str:
    if stats.total == 0:
        return (
            "No applications were logged in this period. If you did apply to "
            "roles, remember to log them with `python main.py log-application` "
            "or by saying 'log application' - the analysis only sees what's "
            "in data/applications.json."
        )

    lines = [
        f"You submitted {stats.total} application(s) between {stats.since} and {stats.until}.",
    ]
    if stats.by_source:
        parts = ", ".join(f"{n} via {src.upper()}" for src, n in stats.by_source.most_common())
        lines.append(f"Breakdown by source: {parts}.")
    if stats.by_status:
        parts = ", ".join(f"{n} {status}" for status, n in stats.by_status.most_common())
        lines.append(f"Status breakdown: {parts}.")
    if stats.average_match_score is not None:
        lines.append(f"Average job-match score at time of application: {stats.average_match_score:.0%}.")

    interviews = stats.by_status.get("interview", 0) + stats.by_status.get("offer", 0)
    if stats.total:
        rate = interviews / stats.total
        lines.append(f"Interview/offer rate this period: {rate:.0%}.")

    return " ".join(lines)


def _claude_summary(config: AppConfig, stats: PeriodStats) -> str | None:
    if not config.anthropic_api_key:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    client = Anthropic(api_key=config.anthropic_api_key)
    applications_desc = "\n".join(
        f"- {a.title} at {a.company} ({a.source}), applied {a.date_applied}, "
        f"status={a.status}, match_score={a.match_score}"
        for a in stats.applications
    ) or "(none)"

    prompt = f"""Here is a job applicant's application log for the period \
{stats.since} to {stats.until}:

{applications_desc}

Write a concise (120-180 word), encouraging but honest analysis: what's \
working, what isn't (e.g. low match scores, low interview rate, over/under \
reliance on one source), and 2-3 concrete suggestions for the next two \
weeks. Plain text, no markdown headers."""

    response = client.messages.create(
        model=config.anthropic_model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in response.content if getattr(b, "type", None) == "text")


def generate_report(config: AppConfig, weeks: int = 2) -> Path:
    until = date.today()
    since = until - timedelta(weeks=weeks)

    log = ApplicationLog(config.path("applications_log"))
    stats = compute_period_stats(log, since, until)

    narrative = _claude_summary(config, stats) or _templated_summary(stats)

    lines = [
        f"# Application analysis: {stats.since} to {stats.until}",
        "",
        f"- Total applications: {stats.total}",
    ]
    if stats.by_source:
        lines.append("- By source: " + ", ".join(f"{k}: {v}" for k, v in stats.by_source.items()))
    if stats.by_status:
        lines.append("- By status: " + ", ".join(f"{k}: {v}" for k, v in stats.by_status.items()))
    if stats.average_match_score is not None:
        lines.append(f"- Average match score: {stats.average_match_score:.0%}")

    lines += ["", "## Summary", "", narrative, "", "## Applications this period", ""]

    if stats.applications:
        lines.append("| Date | Title | Company | Source | Status | Match |")
        lines.append("|---|---|---|---|---|---|")
        for a in sorted(stats.applications, key=lambda x: x.date_applied):
            match = f"{a.match_score:.0%}" if a.match_score is not None else "-"
            lines.append(f"| {a.date_applied} | {a.title} | {a.company} | {a.source} | {a.status} | {match} |")
    else:
        lines.append("(none logged)")

    report_text = "\n".join(lines) + "\n"

    output_dir = config.path("output_dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"analysis_{stats.since}_{stats.until}.md"
    out_path.write_text(report_text, encoding="utf-8")
    return out_path
