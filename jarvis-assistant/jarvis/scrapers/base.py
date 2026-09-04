"""Generic, config-driven HTML job-listing scraper.

Selectors live in config.yaml rather than in code, on the assumption that
career-site markup will need re-tuning after launch (this project shipped
without the ability to verify selectors against the live FCA/BoE pages -
see README). Use `python main.py inspect <source>` to calibrate them.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from jarvis.config import SourceConfig

USER_AGENT = (
    "Mozilla/5.0 (compatible; JavisJobAssistant/1.0; personal use; "
    "+https://github.com/) requests"
)

REQUEST_TIMEOUT_SECONDS = 20


@dataclass
class JobPosting:
    source: str
    title: str
    link: str
    location: str | None = None
    raw_text: str | None = None


class ScraperError(RuntimeError):
    pass


def fetch(url: str) -> str:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ScraperError(f"Failed to fetch {url}: {exc}") from exc
    return resp.text


def parse_listings(html: str, source_key: str, cfg: SourceConfig) -> list[JobPosting]:
    soup = BeautifulSoup(html, "lxml")
    card_selector = cfg.selectors.get("job_card")
    if not card_selector:
        raise ScraperError(f"No job_card selector configured for source '{source_key}'")

    title_selector = cfg.selectors.get("title")
    location_selector = cfg.selectors.get("location")
    link_is_absolute = bool(cfg.selectors.get("link_is_absolute", False))
    base_url = cfg.selectors.get("base_url", cfg.listing_url)

    postings: list[JobPosting] = []
    seen_links: set[str] = set()

    for card in soup.select(card_selector):
        href = card.get("href")
        if not href:
            a = card.select_one("a[href]")
            href = a.get("href") if a else None
        if not href:
            continue

        link = href if link_is_absolute else urljoin(base_url, href)
        if link in seen_links:
            continue
        seen_links.add(link)

        if title_selector:
            title_el = card.select_one(title_selector)
            title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)
        else:
            title = card.get_text(strip=True)

        if not title:
            continue

        location = None
        if location_selector:
            loc_el = card.select_one(location_selector)
            if loc_el:
                location = loc_el.get_text(strip=True)

        postings.append(
            JobPosting(source=source_key, title=title, link=link, location=location, raw_text=title)
        )

    return postings


def scrape_source(source_key: str, cfg: SourceConfig) -> list[JobPosting]:
    html = fetch(cfg.listing_url)
    return parse_listings(html, source_key, cfg)
