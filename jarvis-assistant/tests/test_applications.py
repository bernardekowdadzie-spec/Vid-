from datetime import date, timedelta

from jarvis.applications import Application, ApplicationLog


def test_append_and_load_roundtrip(tmp_path):
    log = ApplicationLog(tmp_path / "applications.json")
    app = Application.new(title="Risk Analyst", company="FCA", source="fca", link="https://example.com")
    log.append(app)

    loaded = log.load()
    assert len(loaded) == 1
    assert loaded[0].title == "Risk Analyst"
    assert loaded[0].id == app.id


def test_in_range_filters_by_date(tmp_path):
    log = ApplicationLog(tmp_path / "applications.json")
    today = date.today()
    old = today - timedelta(days=30)

    log.append(Application.new(title="Old role", company="BoE", source="boe", link="x", date_applied=old.isoformat()))
    log.append(Application.new(title="Recent role", company="FCA", source="fca", link="y", date_applied=today.isoformat()))

    since = today - timedelta(days=14)
    results = log.in_range(since, today)

    assert len(results) == 1
    assert results[0].title == "Recent role"
