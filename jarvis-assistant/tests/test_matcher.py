from jarvis.matcher import rank_postings, score_posting
from jarvis.scrapers.base import JobPosting

SKILLS_PROFILE = {
    "skills": ["AML", "risk management", "python"],
    "seniority_levels": ["manager"],
    "qualifications": ["CFA"],
    "excluded_keywords": ["graduate scheme"],
}


def test_score_posting_matches_skills():
    posting = JobPosting(
        source="fca",
        title="AML Risk Manager",
        link="https://example.com/1",
        raw_text="AML Risk Manager - lead our risk management function, python skills a plus",
    )
    result = score_posting(posting, SKILLS_PROFILE)
    assert result is not None
    assert result.score > 0
    assert "AML" in result.matched_keywords


def test_score_posting_excludes_excluded_keywords():
    posting = JobPosting(
        source="fca",
        title="Graduate Scheme - AML Analyst",
        link="https://example.com/2",
        raw_text="Graduate Scheme - AML Analyst",
    )
    result = score_posting(posting, SKILLS_PROFILE)
    assert result is None


def test_score_posting_no_match_scores_zero():
    posting = JobPosting(
        source="boe",
        title="Facilities Coordinator",
        link="https://example.com/3",
        raw_text="Facilities Coordinator - manage building operations",
    )
    result = score_posting(posting, SKILLS_PROFILE)
    assert result is not None
    assert result.score == 0.0


def test_rank_postings_respects_minimum_score_and_top_n():
    postings = [
        JobPosting(source="fca", title="AML Risk Manager", link="a", raw_text="AML risk management python"),
        JobPosting(source="boe", title="Facilities Coordinator", link="b", raw_text="building operations"),
        JobPosting(source="fca", title="Risk Analyst", link="c", raw_text="risk management"),
    ]
    results = rank_postings(postings, SKILLS_PROFILE, minimum_score=0.1, top_n=1)
    assert len(results) == 1
    assert results[0].posting.link == "a"
