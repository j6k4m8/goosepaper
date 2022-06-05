import requests
from typing import List

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
        timezone: str = "America%2FNew_York",
        **kwargs,
    ):
        self.lat = lat
        self.lon = lon
        self.F = F
        self.timezone = timezone.replace("/", "%2F")
        if "woe" in kwargs:
            raise ValueError(
                "OpenMeteoWeatherStoryProvider does not support WOEIDs. Please pass a lat and lon instead."
            )

    def _weather_code_to_string(self, code: int):
        return (
            _WEATHER_CODES[code]
            if code in _WEATHER_CODES
            else "Unknown weather code [{}]".format(code)
        )

    def _build_url(self):
        return (
            f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}"
            f"&longitude={self.lon}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&temperature_unit={'fahrenheit' if self.F else 'celsius'}&timezone={self.timezone}"
        )

    def get_stories(self, limit: int = 1, **kwargs) -> List[Story]:
        res = requests.get(self._build_url()).json()
        daily = res["daily"]
        todays_high = daily["temperature_2m_max"][0]
        todays_low = daily["temperature_2m_min"][0]
        # todays_precip = daily["precipitation_sum"][0]
        weathercode_string = self._weather_code_to_string(daily["weathercode"][0])
        headline = f"{todays_high:.1f}ºF/{todays_low:.1f}ºF"
        return [
            Story(
                headline=headline,
                body_text=f"{weathercode_string}",  #  with {todays_precip:.1f}mm of rain
                placement_preference=PlacementPreference.EAR,
            )
        ]
