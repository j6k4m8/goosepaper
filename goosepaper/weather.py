import requests
from typing import List

from goosepaper.util import StoryProvider, PlacementPreference
from goosepaper.story import Story


class WeatherStoryProvider(StoryProvider):
    def __init__(self, woe: str = "2358820", F: bool = True):
        self.woe = woe
        self.F = F

    def CtoF(self, temp: float) -> float:
        return (temp * 9 / 5) + 32

    def get_stories(self, limit: int = 1) -> List[Story]:
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
