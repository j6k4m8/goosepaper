# Weather

The `weather` source fetches a forecast from Open-Meteo. Depending on its mode, it
renders a compact front-page "ear", an hourly utility strip, a daily strip, or both.

## Configuration

```json
{
  "type": "weather",
  "lat": 36.5,
  "lon": -75.1,
  "unit": "F",
  "timezone": "America/New_York",
  "mode": "hourly_daily",
  "hours": 12,
  "step_hours": 4,
  "days": 4,
  "clock_format": "12h"
}
```

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `lat` | Yes | — | Numeric latitude passed to Open-Meteo. |
| `lon` | Yes | — | Numeric longitude passed to Open-Meteo. |
| `unit` | No | `F` | `F` for Fahrenheit or `C` for Celsius. |
| `timezone` | No | `America/New_York` | Non-empty timezone name passed to Open-Meteo and used to choose upcoming hours. |
| `mode` | No | `summary` | `summary`, `hourly`, `daily`, or `hourly_daily`. |
| `hours` | No | `12` | Positive hourly forecast window. |
| `step_hours` | No | `4` | Positive stride used to sample points in the hourly window. |
| `days` | No | `4` | Positive daily forecast length; Open-Meteo requests are capped at 16 days. |
| `clock_format` | No | `12h` | `12h` or `24h` labels for hourly forecasts. |

## Modes

- `summary` renders today's high, low, and condition as a compact ear.
- `hourly` samples the next `hours` using `step_hours`. It uses a compact ear when
  `hours` is no greater than `step_hours`; otherwise it renders a utility strip.
- `daily` renders up to `days` daily forecasts. It uses a compact ear for one day
  and a utility strip for longer forecasts.
- `hourly_daily` combines the hourly and daily strips.

The source requires network access to `https://api.open-meteo.com` and uses latitude
and longitude to select the forecast location.
