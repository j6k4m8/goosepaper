# Mastodon posts

The `mastodon` source reads the public RSS feed for one account and turns each post
into a story.

## Configuration

```json
{
  "type": "mastodon",
  "server": "https://neuromatch.social",
  "username": "jordan",
  "limit": 4,
  "since_days_ago": 1
}
```

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `server` | Yes | — | Non-empty Mastodon server URL. A trailing slash is removed. |
| `username` | Yes | — | Non-empty account name. A leading `@` is accepted. |
| `limit` | No | `5` | Positive maximum number of posts to return. |
| `since_days_ago` | No | No cutoff | A positive value includes entries published within this many days; `0` behaves like omission. |

The provider reads `<server>/@<username>.rss`, so it needs network access but no
Mastodon token. The configured server must expose the account's public RSS feed.
