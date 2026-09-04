from jarvis.config import AppConfig
from jarvis.scrapers.base import JobPosting, scrape_source


def scrape(config: AppConfig) -> list[JobPosting]:
    cfg = config.source("fca")
    return scrape_source("fca", cfg)
