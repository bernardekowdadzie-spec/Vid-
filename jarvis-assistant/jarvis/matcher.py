"""Keyword-based scoring of job postings against a skills profile.

Deliberately simple and dependency-free (no embeddings/API call needed) so
a scan works even without an Anthropic API key. Score is 0-1: the fraction
of your skills/qualifications/seniority keywords found in the job's title
(and description text, when a scraper is able to capture it).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from jarvis.scrapers.base import JobPosting


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower())


@dataclass
class MatchResult:
    posting: JobPosting
    score: float
    matched_keywords: list[str]


def score_posting(posting: JobPosting, skills_profile: dict) -> MatchResult | None:
    text = _normalize(posting.raw_text or posting.title)

    excluded = [_normalize(k) for k in skills_profile.get("excluded_keywords", [])]
    if any(k and k in text for k in excluded):
        return None

    skills = skills_profile.get("skills", [])
    seniority = skills_profile.get("seniority_levels", [])
    qualifications = skills_profile.get("qualifications", [])

    weighted_terms = (
        [(s, 1.0) for s in skills]
        + [(s, 0.5) for s in seniority]
        + [(s, 0.3) for s in qualifications]
    )
    if not weighted_terms:
        return None

    total_weight = sum(w for _, w in weighted_terms)
    matched: list[str] = []
    earned = 0.0
    for term, weight in weighted_terms:
        norm_term = _normalize(term)
        if norm_term and norm_term in text:
            matched.append(term)
            earned += weight

    score = earned / total_weight if total_weight else 0.0
    return MatchResult(posting=posting, score=round(score, 3), matched_keywords=matched)


def rank_postings(
    postings: list[JobPosting],
    skills_profile: dict,
    minimum_score: float = 0.35,
    top_n: int = 10,
) -> list[MatchResult]:
    results = []
    for posting in postings:
        result = score_posting(posting, skills_profile)
        if result is not None and result.score >= minimum_score:
            results.append(result)

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]
