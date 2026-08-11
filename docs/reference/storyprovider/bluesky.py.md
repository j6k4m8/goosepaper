# Bluesky posts

The `bluesky` source reads one account through Bluesky's public AppView API. Posts
become short stories in a Bluesky section; reposts are skipped.

## Configuration

```json
{
  "type": "bluesky",
  "username": "jordan.matelsky.com",
  "limit": 4,
  "since_days_ago": 1,
  "include_replies": false
}
```

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `username` | Yes | — | Non-empty Bluesky handle. A leading `@` is accepted. |
| `limit` | No | `5` | Positive maximum number of posts to request and return. |
| `since_days_ago` | No | No cutoff | A positive value includes posts created within this many days; `0` behaves like omission. |
| `include_replies` | No | `true` | Whether the author feed should include replies. |

The provider uses `https://public.api.bsky.app` and does not require Bluesky
credentials. It preserves paragraph breaks and escapes post text before rendering it
as HTML.
