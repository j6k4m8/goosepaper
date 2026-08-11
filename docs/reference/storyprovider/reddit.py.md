# Reddit headlines

The `reddit` source reads a subreddit's public RSS feed. Each post title becomes a
short sidebar story with the post author and subreddit in its byline.

## Configuration

```json
{
  "type": "reddit",
  "subreddit": "todayilearned",
  "limit": 6,
  "since_days_ago": 1
}
```

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `subreddit` | Yes | — | Non-empty subreddit name. `news`, `r/news`, and `/r/news/` are normalized to `news`. |
| `limit` | No | `20` | Positive maximum number of posts to return. |
| `since_days_ago` | No | No cutoff | A positive value includes entries updated within this many days; `0` behaves like omission. |

The provider requests `https://www.reddit.com/r/<subreddit>.rss`. It needs network
access but does not require Reddit credentials.
