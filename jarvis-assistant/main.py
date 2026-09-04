#!/usr/bin/env python3
"""CLI entrypoint for Javis.

Usage:
  python main.py listen                     # full voice loop
  python main.py scan                       # one-off job scan, no mic
  python main.py tailor <job-link>           # tailor CV for a job from the last scan, by link
  python main.py analyze [--weeks N]         # one-off application analysis
  python main.py inspect <fca|boe>           # calibrate scraper selectors
  python main.py log-application --title ... --company ... --source ... --link ...
"""

from __future__ import annotations

import argparse
import sys

from jarvis.config import ConfigError, load_config


def cmd_listen(args: argparse.Namespace) -> None:
    from jarvis.voice import Javis

    config = load_config()
    Javis(config).run_forever()


def cmd_scan(args: argparse.Namespace) -> None:
    from jarvis.scheduler import run_scan

    config = load_config()
    matches = run_scan(config)
    if not matches:
        print("No matches found above the minimum score.")
        return
    for i, match in enumerate(matches, start=1):
        print(f"{i}. [{match.score:.0%}] {match.posting.title} ({match.posting.source.upper()}) - {match.posting.link}")


def cmd_tailor(args: argparse.Namespace) -> None:
    from jarvis.scheduler import run_scan, run_tailor

    config = load_config()
    matches = run_scan(config)
    match = next((m for m in matches if m.posting.link == args.link), None)
    if match is None:
        print(f"No match with link {args.link} found in a fresh scan. Run `scan` first to see valid links.")
        sys.exit(1)
    out_path = run_tailor(config, match)
    print(f"Tailored CV saved to {out_path}")


def cmd_analyze(args: argparse.Namespace) -> None:
    from jarvis.scheduler import run_analysis

    config = load_config()
    out_path = run_analysis(config, weeks=args.weeks)
    print(f"Analysis saved to {out_path}")
    print(out_path.read_text(encoding="utf-8"))


def cmd_inspect(args: argparse.Namespace) -> None:
    from jarvis.scrapers.inspect import inspect_source

    config = load_config()
    inspect_source(config, args.source)


def cmd_log_application(args: argparse.Namespace) -> None:
    from jarvis.applications import Application, ApplicationLog

    config = load_config()
    log = ApplicationLog(config.path("applications_log"))
    application = Application.new(
        title=args.title,
        company=args.company,
        source=args.source,
        link=args.link,
        match_score=args.match_score,
        status=args.status,
        notes=args.notes or "",
    )
    log.append(application)
    print(f"Logged application: {application.title} at {application.company} ({application.id})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Javis - FCA/BoE job assistant")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("listen", help="Run the full voice wake/sleep loop").set_defaults(func=cmd_listen)
    sub.add_parser("scan", help="Run a one-off job scan").set_defaults(func=cmd_scan)

    p_tailor = sub.add_parser("tailor", help="Tailor a CV for one job from a fresh scan")
    p_tailor.add_argument("link", help="Job posting link, as printed by `scan`")
    p_tailor.set_defaults(func=cmd_tailor)

    p_analyze = sub.add_parser("analyze", help="Run the application analysis")
    p_analyze.add_argument("--weeks", type=int, default=2)
    p_analyze.set_defaults(func=cmd_analyze)

    p_inspect = sub.add_parser("inspect", help="Fetch a source page to calibrate selectors")
    p_inspect.add_argument("source", choices=["fca", "boe"])
    p_inspect.set_defaults(func=cmd_inspect)

    p_log = sub.add_parser("log-application", help="Manually log a submitted application")
    p_log.add_argument("--title", required=True)
    p_log.add_argument("--company", required=True)
    p_log.add_argument("--source", required=True, choices=["fca", "boe", "other"])
    p_log.add_argument("--link", required=True)
    p_log.add_argument("--match-score", type=float, default=None)
    p_log.add_argument("--status", default="submitted", choices=["submitted", "interview", "rejected", "offer", "withdrawn"])
    p_log.add_argument("--notes", default="")
    p_log.set_defaults(func=cmd_log_application)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
