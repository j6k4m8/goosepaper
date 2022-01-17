# Customizing Your Feed

## Example config

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
                "rss_path": "https://feeds.npr.org/1001/rss.xml",
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

## Look & Feel

### Titles and font size

In the first part of the config you can set global parameters for your goosepaper. These do not need to be set as they have default parameters.

### Goosepaper Title

The title is at the top of the first page if your paper. The default value is "Daily Goosepaper" but you can change it like this:

```json
"title" : "Jordan's Daily Goosepaper"
```

### Subtitle

The subtitle is at the second line at the top of the first page after yout title.

```json
"subtitle" : ""
```

### Font Size

The fontsize determines the fontsize for all text in the goosepaper. Other text will be scaled accordingly, so a large body font will generally correspond (ideally, if the style is well-built) with larger headliner font sizes as well. The default is 12.

```json
"font_size" : 14
```

(This only matters if your output is set as a `.pdf`)

### Styles

There are a few prepackaged stylesheets that can be applied to your goosepaper. The default is `"FifthAvenue"`. You can change this to any of the following:

    -   Academy
    -   FifthAvenue
    -   Autumn

For more information on the styles and to see a gallery of the different stylesheets on the same goosepaper content, see the [Style Gallery](StyleGallery.md) page.

## Stories and StoryProviders

Stories in a Goosepaper are created by a StoryProvider. You can think of a StoryProvider as a "source." So you might have Twitter stories (`TwitterStoryProvider`), some blog posts (`RSSFeedStoryProvider`), etc.

This section aims to be a comprehensive list of all storyproviders and how to configure them.
(This was the case at time of writing.)

In addition to the storyproviders listed here, there is also a separate repository, [auxilliary-goose](https://github.com/j6k4m8/auxiliary-goose/), where you can find additional storyproviders. For info on how to customize these check out the documentation in said repository.

Stories and storyproviders are given in the config-file using the `"stories"`-key in the following way:
(remember correct comma-separation in this file).

```json
"stories" : [
	{
		"provider" 	: "Storyprovider1",
		"config" 	: {
			"PARAMETER"	: "VALUE",
			"PARAMETER"	: "VALUE"
		}
	},
	{
		"provider" 	: "Storyprovider2",
		"config" 	: {
			"PARAMETER"	: "VALUE",
			"PARAMETER"	: "VALUE"
		}
	},
]
```

Right now, these are the storyproviders built into this repository:

-   [CustomText](#CustomText)
-   [Reddit](#Reddit)
-   [RSS](#RSS)
-   [Twitter](#Twitter)
-   [Weather](#Weather)
-   [Wikipedia Current Events](#Wikipedia)

### <a name="CustomText">CustomTextStoryProvider</a>

```json
"provider": "text"
```

This storyprovider fills paragraphs with your own custom text, or with Lorem Ipsum text if you don't provide anything.

#### Paramaeters:

| Parameter  | Type | Default | Description                                                    |
| ---------- | ---- | ------- | -------------------------------------------------------------- |
| `headline` | str  | None    | The text to use. If not provided, the default is Lorem Ipsum.  |
| `text`     | str  | None    | The text to use. If not provided, the default is Lorem Ipsum.  |
| `limit`    | int  | 5       | The number of paragraphs to generate, if text is not provided. |

#### Example:

```json
{
    "provider": "text",
    "config": {
        "headline": "This is a headline",
        "text": "This is some text"
    }
}
```

### <a name="Reddit">Reddit</a>

```json
"provider"	: "reddit"
```

This storyprovider gives headlines from a selected subreddit given in config file. The story gives the title, the username of the poster, and some text.

#### Parameters:

| Parameter        | Type | Default | Description                             |
| ---------------- | ---- | ------- | --------------------------------------- |
| `subreddit`      | str  | None    | The subreddit to use.                   |
| `limit`          | int  | 20      | The number of stories to get.           |
| `since_days_ago` | int  | None    | If provided, filter stories by recency. |

### <a name="RSS">RSS</a>

```json
"provider"	: "rss"
```

Returns results from a given RSS feed. Feed URL must be specified in the config file.

The parameter `rss_path` has to be given a value in configfile.
Default limiting value is `5`.

#### Parameters:

| Parameter        | Type | Default | Description                             |
| ---------------- | ---- | ------- | --------------------------------------- |
| `rss_path`       | str  | None    | The RSS feed to use.                    |
| `limit`          | int  | 5       | The number of stories to get.           |
| `since_days_ago` | int  | None    | If provided, filter stories by recency. |

### <a name="Twitter">Twitter</a>

```json
"provider"	: "twitter"
```

Returns tweets from given users.

#### Parameters:

| Parameter        | Type             | Default | Description                                                 |
| ---------------- | ---------------- | ------- | ----------------------------------------------------------- |
| `usernames`      | str or list[str] | None    | Twitter usernames to use. Can be a single username or list. |
| `limit`          | int              | 8       | The number of stories to get.                               |
| `since_days_ago` | int              | None    | If provided, filter stories by recency.                     |

### <a name="Weather">Weather</a>

```json
"provider"	: "weather"
```

Get the weather forecast for the day. This story provider is placed in the "ear" of the Goosepaper front page, as you'd expect on a real newspaper.

The weatherdata for this storyprovider is collected from [www.metaweather.com](https://www.metaweather.com/).

#### Parameters:

| Parameter | Type | Default | Description                                                 |
| --------- | ---- | ------- | ----------------------------------------------------------- |
| `woe`     | str  | None    | The WOEID of your location. See [here](www.metaweather.com) |
| `F`       | bool | True    | If set to True, the forecast will be in Fahrenheit.         |

### <a name="Wikipedia">Wikipedia Current Events</a>

```json
"provider"	: "wikipedia_current_events"
```

Returns current events section from Wikipedia.

There are no configurable parameters for this story provider.
