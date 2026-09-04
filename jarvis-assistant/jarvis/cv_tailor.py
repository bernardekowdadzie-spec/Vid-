"""Uses Claude (Anthropic API) to tailor the base CV to a specific job posting.

Requires ANTHROPIC_API_KEY to be set (in .env or the environment). This
calls out to the Anthropic API with your CV and profile content - review
Anthropic's data handling terms if that matters for your use case.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from anthropic import Anthropic

from jarvis.config import AppConfig
from jarvis.matcher import MatchResult

SYSTEM_PROMPT = """You are a careful, honest CV/resume editor helping a job \
applicant tailor their existing CV to a specific vacancy at a UK financial \
regulator. Rules:
- Never invent experience, employers, dates, qualifications, or numbers \
that are not present in the base CV.
- You may reorder, re-emphasize, rephrase, and select which existing \
bullets to foreground based on relevance to the job.
- Rewrite the profile/summary section to speak directly to the role.
- Keep the output in the same Markdown structure as the input CV.
- After the CV, add a section "## Why this role" with 3-4 bullet points \
explaining, in the applicant's own likely voice, why their existing \
background fits this specific posting - grounded only in the base CV.
"""


def _slugify(text: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in text]
    slug = "".join(keep)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:60]


def tailor_cv(config: AppConfig, match: MatchResult) -> Path:
    if not config.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to jarvis-assistant/.env "
            "to use CV tailoring."
        )

    client = Anthropic(api_key=config.anthropic_api_key)

    posting = match.posting
    user_prompt = f"""BASE CV:
---
{config.base_cv}
---

SKILLS PROFILE (for context, not to be pasted verbatim):
{config.skills_profile}

JOB POSTING:
Title: {posting.title}
Source: {posting.source}
Link: {posting.link}
Location: {posting.location or "unspecified"}
Matched keywords: {", ".join(match.matched_keywords) or "none"}

Produce the tailored CV now."""

    response = client.messages.create(
        model=config.anthropic_model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    tailored_text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )

    output_dir = config.path("output_dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"cv_{_slugify(posting.source)}_{_slugify(posting.title)}_{date.today().isoformat()}.md"
    out_path = output_dir / filename
    out_path.write_text(tailored_text, encoding="utf-8")
    return out_path
