import datetime
from html import escape
from typing import List
from zoneinfo import ZoneInfo

import requests

from ..util import PlacementPreference
from .storyprovider import StoryProvider
from ..story import Story


class MetaWeatherStoryProvider(StoryProvider):
    def __init__(self, woe: str = "2358820", F: bool = True):
        self.woe = woe
        self.F = F

    def CtoF(self, temp: float) -> float:
        return (temp * 9 / 5) + 32

    def get_stories(self, limit: int = 1, **kwargs) -> List[Story]:
        weatherReq = requests.get(
            f"https://www.metaweather.com/api/location/{self.woe}/"
        ).json()
        weather = weatherReq["consolidated_weather"][0]
        weatherTitle = weatherReq["title"]
        if self.F:
            headline = f"{int(self.CtoF(weather['the_temp']))}ºF with {weather['weather_state_name']} in {weatherTitle}"
            body_html = f"""
            <img
                src="https://www.metaweather.com/static/img/weather/png/64/{weather['weather_state_abbr']}.png"
                width="42" />
            {int(self.CtoF(weather['min_temp']))} – {int(self.CtoF(weather['max_temp']))}ºF, Winds {weather['wind_direction_compass']}
            """
        else:
            headline = f"{weather['the_temp']:.1f}ºC with {weather['weather_state_name']} in {weatherTitle}"
            body_html = f"""
            <img
                src="https://www.metaweather.com/static/img/weather/png/64/{weather['weather_state_abbr']}.png"
                width="42" />
            {weather['min_temp']:.1f} – {weather['max_temp']:.1f}ºC, Winds {weather['wind_direction_compass']}
            """
        return [
            Story(
                headline=headline,
                body_html=body_html,
                placement_preference=PlacementPreference.EAR,
            )
        ]


_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Heavy drizzle",
    56: "Light freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light rain showers",
    81: "Moderate rain showers",
    82: "Heavy rain showers",
    85: "Light snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorms",
    96: "Thunderstorms with hail",
    99: "Thunderstorms with heavy hail",
}


class OpenMeteoWeatherStoryProvider(StoryProvider):
    def __init__(
        self,
        lat: float,
        lon: float,
        F: bool = True,
        timezone: str = "America/New_York",
        mode: str = "summary",
        hours: int = 12,
        step_hours: int = 4,
        days: int = 4,
        clock_format: str = "12h",
        **kwargs,
    ):
        self.lat = lat
        self.lon = lon
        self.F = F
        self.timezone = timezone
        self.mode = mode
        self.hours = hours
        self.step_hours = step_hours
        self.days = days
        self.clock_format = clock_format
        if "woe" in kwargs:
            raise ValueError(
                "OpenMeteoWeatherStoryProvider does not support WOEIDs. Please pass a lat and lon instead."
            )
        if self.mode not in {"summary", "hourly", "daily", "hourly_daily"}:
            raise ValueError(
                'Weather mode must be one of "summary", "hourly", "daily", or "hourly_daily".'
            )
        if self.hours <= 0 or self.step_hours <= 0 or self.days <= 0:
            raise ValueError("Weather hours, step_hours, and days must be positive.")
        if self.clock_format not in {"12h", "24h"}:
            raise ValueError('Weather clock_format must be either "12h" or "24h".')

    def _weather_code_to_string(self, code: int):
        return (
            _WEATHER_CODES[code]
            if code in _WEATHER_CODES
            else "Unknown weather code [{}]".format(code)
        )

    def _build_params(self):
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "temperature_unit": "fahrenheit" if self.F else "celsius",
            "timezone": self.timezone,
        }
        if self.mode in {"summary", "daily", "hourly_daily"}:
            params["daily"] = "weather_code,temperature_2m_max,temperature_2m_min"
            params["forecast_days"] = 1 if self.mode == "summary" else max(1, min(self.days, 16))
        if self.mode in {"hourly", "hourly_daily"}:
            params["hourly"] = "weather_code,temperature_2m"
        return params

    def _local_now(self) -> datetime.datetime:
        try:
            now = datetime.datetime.now(ZoneInfo(self.timezone))
        except Exception:
            now = datetime.datetime.now()
        return now.replace(minute=0, second=0, microsecond=0, tzinfo=None)

    def _placement_preference(self) -> PlacementPreference:
        if self.mode == "summary":
            return PlacementPreference.EAR
        if self.mode == "hourly_daily":
            return PlacementPreference.UTILITY
        if self.mode == "daily" and self.days <= 1:
            return PlacementPreference.EAR
        if self.mode == "hourly" and self.hours <= self.step_hours:
            return PlacementPreference.EAR
        return PlacementPreference.UTILITY

    def _unit(self) -> str:
        return "F" if self.F else "C"

    def _temp_label(self, value: float, *, compact: bool = False) -> str:
        precision = 0 if compact else 1
        return f"{value:.{precision}f}º{self._unit()}"

    def _compact_story(self, headline: str, body_text: str) -> Story:
        return Story(
            headline=headline,
            body_text=body_text,
            placement_preference=PlacementPreference.EAR,
            include_in_toc=False,
            short_form=True,
        )

    def _utility_story(self, modules_html: str) -> Story:
        return Story(
            headline="Weather",
            body_html=(
                f'<div class="weather-module">'
                f"{modules_html}"
                f"</div>"
            ),
            placement_preference=PlacementPreference.UTILITY,
            include_in_toc=False,
            short_form=True,
        )

    def _utility_table_module(self, kicker: str, columns_html: str) -> str:
        return (
            '<div class="weather-module__section">'
            f'<p class="weather-kicker">{escape(kicker)}</p>'
            f'<table class="weather-table"><tbody><tr>{columns_html}</tr></tbody></table>'
            "</div>"
        )

    def _utility_text_module(self, kicker: str, text: str) -> str:
        return (
            '<div class="weather-module__section">'
            f'<p class="weather-kicker">{escape(kicker)}</p>'
            f'<p class="weather-empty">{escape(text)}</p>'
            "</div>"
        )

    def _render_weather_cell(self, label: str, temp: str, condition: str) -> str:
        return (
            '<td class="weather-table__cell">'
            f'<span class="weather-cell__label">{escape(label)}</span>'
            f'<span class="weather-cell__temp">{escape(temp)}</span>'
            f'<span class="weather-cell__condition">{escape(condition)}</span>'
            "</td>"
        )

    def _build_summary_story(self, payload: dict) -> Story:
        daily = payload["daily"]
        todays_high = daily["temperature_2m_max"][0]
        todays_low = daily["temperature_2m_min"][0]
        weathercode_string = self._weather_code_to_string(daily["weather_code"][0])
        return self._compact_story(
            headline=f"{self._temp_label(todays_high)}/{self._temp_label(todays_low)}",
            body_text=weathercode_string,
        )

    def _build_daily_story(self, payload: dict) -> Story:
        daily = payload["daily"]
        if self._placement_preference() == PlacementPreference.EAR:
            return self._compact_story(
                headline=(
                    f"{self._temp_label(daily['temperature_2m_max'][0])}/"
                    f"{self._temp_label(daily['temperature_2m_min'][0])}"
                ),
                body_text=self._weather_code_to_string(daily["weather_code"][0]),
            )

        return self._utility_story(self._daily_module_html(payload))

    def _build_hourly_story(self, payload: dict) -> Story:
        hourly = payload["hourly"]
        entries = self._select_hourly_entries(hourly)
        if not entries:
            return self._compact_story(headline="Weather", body_text="No hourly forecast available")
        if self._placement_preference() == PlacementPreference.EAR:
            label, temp, condition = entries[0]
            return self._compact_story(headline=temp, body_text=f"{label} · {condition}")

        return self._utility_story(self._hourly_module_html(payload))

    def _build_hourly_daily_story(self, payload: dict) -> Story:
        return self._utility_story(
            self._hourly_module_html(payload) + self._daily_module_html(payload)
        )

    def _daily_module_html(self, payload: dict) -> str:
        daily = payload["daily"]
        count = min(
            self.days,
            len(daily["time"]),
            len(daily["temperature_2m_max"]),
            len(daily["temperature_2m_min"]),
            len(daily["weather_code"]),
        )
        columns = []
        for index in range(count):
            label = self._daily_label(index, daily["time"][index])
            temp = (
                f"{self._temp_label(daily['temperature_2m_max'][index], compact=True)}/"
                f"{self._temp_label(daily['temperature_2m_min'][index], compact=True)}"
            )
            condition = self._weather_code_to_string(daily["weather_code"][index])
            columns.append(self._render_weather_cell(label, temp, condition))
        kicker = f"Next {count} Day" + ("s" if count != 1 else "")
        return self._utility_table_module(kicker, "".join(columns))

    def _hourly_module_html(self, payload: dict) -> str:
        hourly = payload["hourly"]
        entries = self._select_hourly_entries(hourly)
        if not entries:
            return self._utility_text_module("Next 0 Hours", "No hourly forecast available")
        columns = [
            self._render_weather_cell(label, temp, condition)
            for label, temp, condition in entries
        ]
        kicker = f"Next {self.hours} Hours"
        return self._utility_table_module(kicker, "".join(columns))

    def _daily_label(self, index: int, date_string: str) -> str:
        if index == 0:
            return "Today"
        if index == 1:
            return "Tomorrow"
        try:
            parsed = datetime.date.fromisoformat(date_string)
        except ValueError:
            return f"Day {index + 1}"
        return parsed.strftime("%a")

    def _select_hourly_entries(self, hourly: dict) -> List[tuple[str, str, str]]:
        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        weather_codes = hourly.get("weather_code", [])
        count = min(len(times), len(temperatures), len(weather_codes))
        if count == 0:
            return []

        start = self._local_now()
        end = start + datetime.timedelta(hours=self.hours)
        hourly_points = []
        for index in range(count):
            try:
                point_time = datetime.datetime.fromisoformat(times[index])
            except ValueError:
                continue
            if point_time < start or point_time > end:
                continue
            hourly_points.append((point_time, temperatures[index], weather_codes[index]))
        if not hourly_points:
            point_time = datetime.datetime.fromisoformat(times[0])
            hourly_points = [(point_time, temperatures[0], weather_codes[0])]

        selected_points = hourly_points[:: self.step_hours]
        return [
            (
                self._hourly_label(point_time),
                self._temp_label(temp, compact=True),
                self._weather_code_to_string(code),
            )
            for point_time, temp, code in selected_points
        ]

    def _hourly_label(self, point_time: datetime.datetime) -> str:
        if self.clock_format == "24h":
            return point_time.strftime("%H:%M")

        hour = point_time.hour % 12 or 12
        suffix = "am" if point_time.hour < 12 else "pm"
        if point_time.minute == 0:
            return f"{hour}{suffix}"
        return f"{hour}:{point_time.minute:02d}{suffix}"

    def get_stories(self, limit: int = 1, **kwargs) -> List[Story]:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=self._build_params(),
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if self.mode == "hourly":
            story = self._build_hourly_story(payload)
        elif self.mode == "hourly_daily":
            story = self._build_hourly_daily_story(payload)
        elif self.mode == "daily":
            story = self._build_daily_story(payload)
        else:
            story = self._build_summary_story(payload)
        return [story]
