"""Orchestrates the actual work: scanning, tailoring, analyzing.

Kept separate from voice.py so the same logic is reachable from the CLI
(no mic needed) and from the voice loop.
"""

from __future__ import annotations

from pathlib import Path

from jarvis.analysis import generate_report
from jarvis.applications import Application, ApplicationLog
from jarvis.config import AppConfig
from jarvis.cv_tailor import tailor_cv
from jarvis.matcher import MatchResult, rank_postings
from jarvis.scrapers import boe, fca
from jarvis.scrapers.base import JobPosting, ScraperError


def run_scan(config: AppConfig) -> list[MatchResult]:
    postings: list[JobPosting] = []
    for label, scraper in (("FCA", fca), ("BoE", boe)):
        try:
            postings.extend(scraper.scrape(config))
        except ScraperError as exc:
            print(f"[warning] {label} scan failed: {exc}")

    matches = rank_postings(
        postings,
        config.skills_profile,
        minimum_score=config.minimum_score,
        top_n=config.top_n_per_scan,
    )
    return matches


def run_tailor(config: AppConfig, match: MatchResult) -> Path:
    return tailor_cv(config, match)


def run_analysis(config: AppConfig, weeks: int = 2) -> Path:
    return generate_report(config, weeks=weeks)


def log_application_from_match(config: AppConfig, match: MatchResult, company: str) -> Application:
    log = ApplicationLog(config.path("applications_log"))
    application = Application.new(
        title=match.posting.title,
        company=company,
        source=match.posting.source,
        link=match.posting.link,
        match_score=match.score,
    )
    log.append(application)
    return application
