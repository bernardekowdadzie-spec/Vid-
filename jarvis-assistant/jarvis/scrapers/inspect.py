"""Helper to calibrate scraper selectors against the real, live page.

Run with `python main.py inspect fca` or `inspect boe` on a machine that can
actually reach the site (this project was built in a sandbox that could
not). Saves the raw HTML to output/ and prints candidate job links plus any
embedded JSON data blocks, so you can quickly write correct CSS selectors
or switch to hitting an underlying JSON API directly.
"""

from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup

from jarvis.config import AppConfig
from jarvis.scrapers.base import fetch

JOB_LINK_PATTERN = re.compile(r"job|vacan|career|role", re.IGNORECASE)


def inspect_source(config: AppConfig, source_key: str) -> None:
    cfg = config.source(source_key)
    print(f"Fetching {cfg.listing_url} ...")
    html = fetch(cfg.listing_url)

    output_dir: Path = config.path("output_dir")
    dump_path = output_dir / f"inspect_{source_key}.html"
    dump_path.write_text(html, encoding="utf-8")
    print(f"Saved raw HTML to {dump_path}")

    soup = BeautifulSoup(html, "lxml")

    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if JOB_LINK_PATTERN.search(href) or JOB_LINK_PATTERN.search(text):
            candidates.append((text[:80], href))

    print(f"\nFound {len(candidates)} candidate job-like links (deduped preview below):")
    seen = set()
    shown = 0
    for text, href in candidates:
        if href in seen:
            continue
        seen.add(href)
        print(f"  [{text!r}] -> {href}")
        shown += 1
        if shown >= 40:
            print("  ... (truncated, see the saved HTML for the full list)")
            break

    json_blocks = soup.find_all("script", attrs={"type": "application/json"})
    next_data = soup.find("script", id="__NEXT_DATA__")
    if json_blocks or next_data:
        print(
            "\nThis page embeds JSON data blocks (application/json script tags "
            "or __NEXT_DATA__). The listings may be easier to pull from that "
            "JSON directly than from HTML selectors - inspect the saved HTML "
            "file for the exact structure."
        )

    print(
        "\nNext step: open the saved HTML (or the live page's dev tools), "
        "identify the CSS selector that uniquely matches each job card/link, "
        "and update sources.%s.selectors in config/config.yaml." % source_key
    )
