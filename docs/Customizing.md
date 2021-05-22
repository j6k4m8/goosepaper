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
Default value is 
```json
"title" : "Daily Goosepaper"
```

### Subtitle

The subtitle is at the second line at the top of the first page after yout title.
Default value is 
```json
"subtitle" : ""
```

### Fontsize

The fontsize determines the fontsize for all text in the goosepaper, but not the title, subtitle, or weather if this i set in `stories`(covered later). The default value is 
```json
"font_size" : 14
```
(This only matters if your ouptup is set as a `.pdf`)
  
## Style

Something about styles needs to go here!!!

## Stories and Storyproviders

The stories is the content you read in your goosepaper, and can be customized in a variety of ways.  
  
This section aims to be a comprehensive list of all storyproviders and how to configure them.  
(This was the case at time of writing.)  
  
In addition to the storyproviders listed here, there is also a separate repository, [auxilliary-goose](https://github.com/j6k4m8/auxiliary-goose/), where you can find additional storyproviders. For info on how to customize these check out the documentation in said repository.

Stories and storyproviders are given in the config-file using the `"stories"`-key in the following way:  
(remember correct comma-separation in this file).

```json
"stories" : [
	{
		"provider" 	: "Storyprovider 1",
		"config" 	: {
			"PARAMETER"	: "VALUE",
			"PARAMETER"	: "VALUE" 
		}
	},
	{
		"provider" 	: "Storyprovider 2",
		"config" 	: {
			"PARAMETER"	: "VALUE",
			"PARAMETER"	: "VALUE" 
		}
	},
]
```
  
As per now these storyproviders are available:
- [Lorem Ipsum](#LoremIpsum)
- [Reddit](#Reddit)
- [RSS](#RSS)
- [Twitter](#Twitter)
- [Weather](#Weather)
- [Wikipedia Current Events](#Wikipedia)
  
### <a name="LoremIpsum">Lorem Ipsum</a>

This storyprovider fills paragraphs with Lorem Ipsum, and is mainly used for testing.
  
Default limiting value is `5`.

Storyprovider name is 
```json
	"provider"	: "lorem"
```

The parameters are as follows:
```json	
	"limit"		:	5 								(int 	- Amount of Lorem Ipsum articles to provide.) 
```
  
### <a name="Reddit">Reddit</a>

This storyprovider gives headlines from a selected subreddit given in config file.  
The story gives the title, the user and some text.
  
The parameter `subreddit` has to be given a value in configfile.  
Default limiting value is `20`.  

Storyprovider name is 
```json
	"provider"	: "reddit"
```

The parameters are as follows:
```json	
	"subreddit"	:	"news"							(str 	- Subreddit you want to see headlines from.) 
	"limit"		:	20 								(int 	- Amount of reddit headlines to provide.) 
```

### <a name="RSS">RSS</a>

Returns results from a given RSS feed. This has to be specified in config file.  
  
The parameter `rss_path` has to be given a value in configfile.  
Default limiting value is `5`.  
  
Storyprovider name is 
```json
	"provider"	: "rss"
```

The parameters are as follows:
```json	
	"rss_path"	:	"https://www.npr.org/feed/"		(str 	- RSS feed you want to see results from.) 
	"limit"		:	20 								(int 	- Amount of reddit headlines to provide.) 
```

### <a name="Twitter">Twitter</a>

Returns tweets from given users. These have to be specified in config file.  
  
The parameter `usernames` has to be given a value in configfile.  
Default limiting value is `8`.  
  
Storyprovider name is 
```json
	"provider"	: "twitter"
```

The parameters are as follows:
```json	
	"usernames"	:	["axios", "NPR"]				([str] 	- Users you want to see results from.) 
	"limit"		:	8 								(int 	- Amount of reddit headlines to provide.) 
```

### <a name="Weather">Weather</a>

Storyprovider for the weatherforecast on the first page.  
The weatherdata for this storyprovider is collected from [www.metaweather.com](https://www.metaweather.com/).  
  
With `example-config.json` the forecast will look something like this:
![Weather forcast with `example-config.json`](exampleWeather.png)  
  
Storyprovider name is 
```json
	"provider"	: "weather"
```

The parameters are as follows:
```json	
	"woe"		:	2358820 						(int 	- Where On Earth, can be collected from 
															  www.metaweather.com. Default is for Boston)
	"F"			:	true/false						(bool 	- Fahreheit(true) or Celsius(false))
```

### <a name="Wikipedia">Wikipedia Current Events</a>

Returns current events section from Wikipedia. These have to be specified in config file.  
  
Storyprovider name is 
```json
	"provider"	: "wikipedia_current_events"
```

The parameters are no parameters for this storyprovider.