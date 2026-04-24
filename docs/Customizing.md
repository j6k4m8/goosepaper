# Customizing Your Feed

Goosepaper now uses a strict v2 config model:

- One paper config file for the paper itself.
- One optional user config file for delivery defaults.
- CLI flags decide whether delivery happens at all.

## Paper Config

Paper configs are JSON files with `"version": 2`.
If you do not pass `--config`, Goosepaper looks for `./goosepaper.json`.

Example:

```json
{
    "version": 2,
    "paper": {
        "title": "Jordan's Daily Goosepaper",
        "subtitle": "",
        "style": "FifthAvenue",
        "font_size": 14,
        "table_of_contents": true,
        "layout": "auto",
        "page_profile": "remarkable2"
    },
    "sources": [
        {
            "type": "weather",
            "lat": 59.3293,
            "lon": 18.0686,
            "unit": "F"
        },
        {
            "type": "wikipedia"
        },
        {
            "type": "rss",
            "url": "https://feeds.npr.org/1001/rss.xml",
            "limit": 5
        },
        {
            "type": "reddit",
            "subreddit": "news"
        }
    ],
    "delivery": {
        "folder": "Morning Brief"
    }
}
```

## User Config

User-level delivery defaults live in `~/.config/goosepaper/config.json`.
These defaults are optional and only affect delivery.

Example:

```json
{
    "version": 2,
    "delivery_defaults": {
        "folder": "News",
        "replace_mode": "nocase",
        "cleanup": false
    }
}
```

Supported `delivery_defaults` fields:

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `folder` | str or null | `null` | Default destination folder on your reMarkable. |
| `replace_mode` | str | `"never"` | Collision behavior. One of `"never"`, `"exact"`, or `"nocase"`. |
| `cleanup` | bool | `false` | Delete the output file after a successful delivery. |

The paper config's `delivery` section only supports `folder`.
Delivery still happens only when you run Goosepaper with `--deliver`.

## CLI Overrides

These flags apply to a single run:

```shell
uv run goosepaper --deliver --folder Inbox --replace-mode exact --cleanup
```

Available delivery flags:

- `--deliver`
- `--folder`
- `--replace-mode`
- `--cleanup`
- `--no-cleanup`

Run-specific options like `--output` and `--nostory` are CLI-only and do not belong in config files.

## Paper Settings

The `paper` object supports:

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `title` | str or null | `null` | The paper title. If omitted, Goosepaper uses its built-in default title. |
| `subtitle` | str or null | `null` | Optional subtitle shown under the title. |
| `style` | str | `"FifthAvenue"` | One of the built-in themes. Themes control typography, rules, spacing, and the general voice of the page. |
| `font_size` | int | `14` | Base reading size for the page. Headings, ears, and utility text scale from this value. |
| `body_font` | str or null | `null` | Optional override for the body font family while keeping the rest of the theme intact. |
| `table_of_contents` | bool | `false` | Optional linked contents block near the top of the issue. In PDF output the links are internal document links. |
| `layout` | str | `"auto"` | Layout override. One of `"auto"`, `"1col"`, `"2col"`, or `"3col"`. |
| `page_profile` | str | `"remarkable2"` | Target page shape. One of `remarkable1`, `remarkable2`, `paper_pro`, `paper_pro_move`, `letter`, or `a4`. (`rm1` also works.) |

Built-in themes:

- `Academy`
- `FifthAvenue`
- `Autumn`
- `GrayMaiden`

With `"layout": "auto"`, Goosepaper chooses a sensible default from the page profile:

- `remarkable1`, `remarkable2`, and `paper_pro_move` default to a single reading column
- `paper_pro`, `letter`, and `a4` default to denser multi-column layouts
- Explicit `"1col"`, `"2col"`, and `"3col"` still override that default

Ears only render when the story mix actually includes `EAR` content, such as weather. The table of contents is independent and only appears when `paper.table_of_contents` is `true`.

`page_profile` is independent of `style` and `layout`. It controls the target page geometry and density envelope so Goosepaper can produce surfaces tuned for:

- `remarkable1`
- `remarkable2`
- `paper_pro`
- `paper_pro_move`
- `letter`
- `a4`

## Sources

The `sources` array describes which providers to include.
Each source entry has a `"type"` plus provider-specific fields.

### Text

```json
{
    "type": "text",
    "headline": "This is a headline",
    "text": "This is some text"
}
```

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `headline` | str | `null` | Headline to use. |
| `text` | str | `null` | Body text to use. |
| `limit` | int | `5` | Number of paragraphs to generate when `text` is omitted. |

### Reddit

```json
{
    "type": "reddit",
    "subreddit": "news"
}
```

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `subreddit` | str | none | The subreddit to use. |
| `limit` | int | `20` | Number of stories to fetch. |
| `since_days_ago` | number | `null` | If provided, filter stories by recency. |

### RSS

```json
{
    "type": "rss",
    "url": "https://feeds.npr.org/1001/rss.xml",
    "limit": 5
}
```

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `url` | str | none | RSS feed URL. |
| `limit` | int | `5` | Number of stories to fetch. |
| `since_days_ago` | number | `null` | If provided, filter stories by recency. |

### Mastodon

```json
{
    "type": "mastodon",
    "server": "https://neuromatch.social",
    "username": "jordan",
    "limit": 8
}
```

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `server` | str | none | Mastodon server URL. |
| `username` | str | none | Mastodon username to use. |
| `limit` | int | `5` | Number of entries to fetch. |
| `since_days_ago` | number | `null` | If provided, filter stories by recency. |

### Weather

```json
{
    "type": "weather",
    "lat": 42.3601,
    "lon": -71.0589,
    "unit": "F"
}
```

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `lat` | number | none | Latitude of the forecast location. |
| `lon` | number | none | Longitude of the forecast location. |
| `unit` | str | `"F"` | Temperature unit. Either `"F"` or `"C"`. |
| `timezone` | str | `"America/New_York"` | Timezone for the forecast request. |

### Wikipedia

```json
{
    "type": "wikipedia"
}
```

This source returns the current events section from Wikipedia.
It does not accept any additional fields.
