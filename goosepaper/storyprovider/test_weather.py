import datetime

from . import weather
from ..util import PlacementPreference


class _FakeResponse:
    def __init__(self, payload, seen=None):
        self._payload = payload
        self._seen = seen

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _forecast_payload():
    return {
        "daily": {
            "time": ["2026-04-24", "2026-04-25", "2026-04-26", "2026-04-27"],
            "temperature_2m_max": [72.0, 69.0, 71.0, 68.0],
            "temperature_2m_min": [58.0, 55.0, 57.0, 54.0],
            "weather_code": [3, 61, 1, 2],
        },
        "hourly": {
            "time": [
                "2026-04-24T12:00",
                "2026-04-24T13:00",
                "2026-04-24T14:00",
                "2026-04-24T15:00",
                "2026-04-24T16:00",
                "2026-04-24T17:00",
                "2026-04-24T18:00",
                "2026-04-24T19:00",
                "2026-04-24T20:00",
                "2026-04-24T21:00",
                "2026-04-24T22:00",
                "2026-04-24T23:00",
                "2026-04-25T00:00",
            ],
            "temperature_2m": [56.0, 57.0, 58.0, 59.0, 60.0, 59.0, 58.0, 57.0, 56.0, 55.0, 54.0, 53.0, 52.0],
            "weather_code": [3, 3, 2, 2, 1, 1, 1, 2, 3, 3, 61, 61, 61],
        },
    }


def test_weather_summary_defaults_to_ear(monkeypatch):
    seen = {}

    def fake_get(url, *, params, timeout):
        seen["url"] = url
        seen["params"] = params
        seen["timeout"] = timeout
        return _FakeResponse(_forecast_payload())

    monkeypatch.setattr(weather.requests, "get", fake_get)

    provider = weather.OpenMeteoWeatherStoryProvider(36.5, -75.1)
    stories = provider.get_stories()

    assert seen["url"] == "https://api.open-meteo.com/v1/forecast"
    assert seen["params"]["daily"] == "weather_code,temperature_2m_max,temperature_2m_min"
    assert seen["timeout"] == 20
    assert len(stories) == 1
    assert stories[0].placement_preference == PlacementPreference.EAR
    assert stories[0].include_in_toc is False
    assert stories[0].headline == "72.0ºF/58.0ºF"
    assert stories[0].plain_text() == "Overcast"


def test_weather_hourly_breakdown_promotes_to_utility_strip(monkeypatch):
    seen = {}

    def fake_get(url, *, params, timeout):
        seen["params"] = params
        return _FakeResponse(_forecast_payload())

    monkeypatch.setattr(weather.requests, "get", fake_get)

    provider = weather.OpenMeteoWeatherStoryProvider(
        36.5,
        -75.1,
        mode="hourly",
        hours=12,
        step_hours=4,
    )
    monkeypatch.setattr(
        provider,
        "_local_now",
        lambda: datetime.datetime(2026, 4, 24, 12, 0, 0),
    )
    stories = provider.get_stories()

    assert seen["params"]["hourly"] == "weather_code,temperature_2m"
    assert len(stories) == 1
    assert stories[0].placement_preference == PlacementPreference.UTILITY
    assert stories[0].include_in_toc is False
    assert stories[0].headline == "Weather"
    assert "Next 12 Hours" in stories[0].body_html
    assert "12pm" in stories[0].body_html
    assert "4pm" in stories[0].body_html
    assert "+4h" not in stories[0].body_html
    assert stories[0].body_html.count('class="weather-table__cell"') == 4


def test_weather_hourly_breakdown_can_use_24h_clock(monkeypatch):
    monkeypatch.setattr(
        weather.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(_forecast_payload()),
    )

    provider = weather.OpenMeteoWeatherStoryProvider(
        36.5,
        -75.1,
        mode="hourly",
        hours=12,
        step_hours=4,
        clock_format="24h",
    )
    monkeypatch.setattr(
        provider,
        "_local_now",
        lambda: datetime.datetime(2026, 4, 24, 12, 0, 0),
    )
    stories = provider.get_stories()

    assert len(stories) == 1
    assert "12:00" in stories[0].body_html
    assert "16:00" in stories[0].body_html
    assert "12pm" not in stories[0].body_html


def test_weather_daily_breakdown_promotes_to_utility_strip(monkeypatch):
    monkeypatch.setattr(
        weather.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(_forecast_payload()),
    )

    provider = weather.OpenMeteoWeatherStoryProvider(
        36.5,
        -75.1,
        mode="daily",
        days=4,
    )
    stories = provider.get_stories()

    assert len(stories) == 1
    assert stories[0].placement_preference == PlacementPreference.UTILITY
    assert "Next 4 Days" in stories[0].body_html
    assert stories[0].body_html.count('class="weather-table__cell"') == 4


def test_weather_hourly_daily_combined_mode_renders_both_sections(monkeypatch):
    seen = {}

    def fake_get(url, *, params, timeout):
        seen["params"] = params
        return _FakeResponse(_forecast_payload())

    monkeypatch.setattr(weather.requests, "get", fake_get)

    provider = weather.OpenMeteoWeatherStoryProvider(
        36.5,
        -75.1,
        mode="hourly_daily",
        hours=12,
        step_hours=4,
        days=4,
    )
    monkeypatch.setattr(
        provider,
        "_local_now",
        lambda: datetime.datetime(2026, 4, 24, 12, 0, 0),
    )
    stories = provider.get_stories()

    assert seen["params"]["hourly"] == "weather_code,temperature_2m"
    assert seen["params"]["daily"] == "weather_code,temperature_2m_max,temperature_2m_min"
    assert len(stories) == 1
    assert stories[0].placement_preference == PlacementPreference.UTILITY
    assert "Next 12 Hours" in stories[0].body_html
    assert "Next 4 Days" in stories[0].body_html
    assert "12pm" in stories[0].body_html
    assert stories[0].body_html.count('class="weather-module__section"') == 2


def test_weather_single_day_daily_mode_stays_compact(monkeypatch):
    monkeypatch.setattr(
        weather.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(_forecast_payload()),
    )

    provider = weather.OpenMeteoWeatherStoryProvider(
        36.5,
        -75.1,
        mode="daily",
        days=1,
    )
    stories = provider.get_stories()

    assert len(stories) == 1
    assert stories[0].placement_preference == PlacementPreference.EAR
    assert stories[0].headline == "72.0ºF/58.0ºF"
