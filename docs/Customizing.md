# Customizing Your Feed

## Example-config

You can choose what content is added to your daily goosepaper by writing your own config-file.
As an example we give the config delivered as an example `example-config.json`:

```json
{
    "font_size": 12,
    "stories": [
        {
            "provider": "weather",
            "config": { "woe": 2358820, "F": true }
        },
        {
            "provider": "twitter",
            "config": {
                "usernames": ["axios", "NPR"],
                "limit_per": 8
            }
        },
        {
            "provider": "wikipedia_current_events",
            "config": {}
        },
        {
            "provider": "rss",
            "config": {
                "rss_path": "https://www.npr.org/feed/",
                "limit": 5
            }
        },
        {
            "provider": "reddit",
            "config": { "subreddit": "news" }
        },
        {
            "provider": "reddit",
            "config": { "subreddit": "todayilearned" }
        }
    ]
}
```

## Titles and fontsize

In the first part of the config you can set global parameters for your goosepaper.
These do not need to be set as they have default parameters.

### Title

The title is at the top of the first page if your paper.
Default value is `"title" : "Daily Goosepaper"`

### Subtitle

The subtitle is at the second line at the top of the first page after yout title.
Default value is `"subtitle" : ""`

### Fontsize

The fontsize determines the fontsize for all text in the goosepaper, but not the title, subtitle, or weather if this i set in `stories`(covered later). The default value is `"font_size" : 14`
(This only matters if your ouptup is set as a `.pdf`)