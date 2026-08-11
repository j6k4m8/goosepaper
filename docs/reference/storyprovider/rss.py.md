# RSS feeds

The `rss` source turns entries from an RSS or Atom feed into stories. Goosepaper can
use content embedded in the feed, a feed summary, or article text extracted from the
linked page.

## Configuration

```json
{
  "type": "rss",
  "url": "https://feeds.npr.org/1001/rss.xml",
  "limit": 5,
  "since_days_ago": 1,
  "byline": "first",
  "body_source": "auto"
}
```

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `url` | Yes | — | Non-empty feed URL. |
| `limit` | No | `5` | Positive maximum number of entries to return. |
| `since_days_ago` | No | No cutoff | A positive value includes entries updated within this many days; `0` behaves like omission. |
| `byline` | No | `all` | `all`, `none`, or `first`; `first` keeps the byline only on the first returned story. |
| `body_source` | No | `auto` | `auto`, `content`, `summary`, or `article`; see below. |

## Body selection

- `auto` uses embedded feed content when present. Otherwise it fetches the linked
  article and runs readability extraction, falling back to the feed body if needed.
- `content` stays within the feed, preferring embedded content and then the summary.
- `summary` prefers the feed summary and falls back to embedded content.
- `article` skips embedded content and tries readability extraction on the linked
  article, falling back to the feed body if the page cannot be used.

Fetching linked articles requires network access in addition to access to the feed.
