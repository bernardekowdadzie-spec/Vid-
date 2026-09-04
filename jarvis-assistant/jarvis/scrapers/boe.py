from jarvis.config import AppConfig
from jarvis.scrapers.base import JobPosting, scrape_source


def scrape(config: AppConfig) -> list[JobPosting]:
    cfg = config.source("boe")
    return scrape_source("boe", cfg)
