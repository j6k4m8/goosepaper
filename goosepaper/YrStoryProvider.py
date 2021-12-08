import requests
from typing import List
from metno_locationforecast import Place, Forecast

from .util import PlacementPreference
from .storyprovider import StoryProvider
from .story import Story


class YrStoryProvider(StoryProvider):
    def __init__(
        self,
        lat: float = 51.477,
        lon: float = 0.000,
        F: bool = False,
        locationName: str = "London",
    ):
        self.F = F
        self.location = Place(locationName, lat, lon)
        self.forecast = Forecast(
            self.location,
            "goosepaper/0.3.1 https://github.com/j6k4m8/goosepaper",
            forecast_type="complete",
        )

    def CtoF(self, temp: float) -> float:
        return (temp * 9 / 5) + 32

    def tempMark(self) -> str:
        # Returns correct temp-unit in string
        if self.F:
            return "ºF"
        return "ºC"

    def get_temps(self, a, b) -> List[float]:
        """
        Return average, max, min temperatures in given time interval
        """
        temps = []

        for i in range(a, b):
            temps.append(
                self.forecast.data.intervals[i].variables["air_temperature"].value
            )

        return [temps[0], max(temps), min(temps)]

    def get_precipitation(self, a: int, b: int) -> float:

        precip = 0
        for i in range(a, b):
            precip += (
                self.forecast.data.intervals[0].variables["precipitation_amount"].value
            )

        return precip

    def get_wind_direction(self, interval: int) -> str:

        direction = (
            self.forecast.data.intervals[interval]
            .variables["wind_from_direction"]
            .value
        )

        direction = direction + 22.5
        if direction > 360:
            direction = direction - 360

        i = int(direction / 45)

        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

        return directions[i]

    def get_wind(self, interval: int) -> List[float]:
        wind_speed = (
            self.forecast.data.intervals[interval].variables["wind_speed"].value
        )
        wind_speed_unit = self.forecast.data.intervals[0].variables["wind_speed"].units

        return [wind_speed, wind_speed_unit]

    def get_cloud_cover(self) -> float:
        return self.forecast.data.intervals[0].variables["cloud_area_fraction"].value

    def get_weather_state(self) -> str:

        temp = self.get_temps(0, 24)[2]
        precip = self.get_precipitation(0, 24)
        cloudCover = self.get_cloud_cover()

        if cloudCover < 20:
            return "sun"

        if cloudCover < 50:
            if precip > 2:
                if temp < 0:
                    return "some snow"

                return "some rain"

            return "fair weather"

        if cloudCover > 50:
            if precip > 2:
                if temp < 0:
                    return "snow"

                return "rain"

            return "clouds"

        raise Exception("Weatherstate error.")

    def get_weather_img(self) -> str:

        state = self.get_weather_state()

        if state == "sun":
            return "c"

        elif state == "fair weather":
            return "lc"

        elif state == "some rain":
            return "s"

        elif state == "some snow":
            return "s"

        elif state == "clouds":
            return "hc"

        elif state == "rain":
            return "lr"

        elif state == "snow":
            return "sn"

        return ""

    def get_stories(self, limit: int = 1) -> List[Story]:
        self.forecast.update()

        self.tom = self.get_temps(0, 24)
        self.wind = self.get_wind(12)

        headline = f"<h2 width=80%>The Weather.</h2>"
        body_html = f"""<span style='font-size:12px;'>Delivered by Met Norway, <a href='http://yr.no'>yr.no</a></span><br>
        {self.tom[0]}{self.tempMark()} with {str(self.get_weather_state())} in {self.location.name}<br>
        <img src="https://www.metaweather.com/static/img/weather/png/64/{self.get_weather_img()}.png" width="5px" /><br>
        {self.tom[2]} – {self.tom[1]}{self.tempMark()}, Winds from {self.get_wind_direction(12)} at {self.wind[0]}{self.wind[1]}.
        """

        return [
            Story(
                headline=headline,
                body_html=body_html,
                placement_preference=PlacementPreference.EAR,
            )
        ]
