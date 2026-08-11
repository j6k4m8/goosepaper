# Readwise Reader documents

The `readwise` source reads documents from the Readwise Reader API. It can filter the
library and render cleaned document text, cleaned article HTML, or the document
summary.

## Authentication

Set a Readwise access token in the environment before running Goosepaper:

```shell
export READWISE_TOKEN="your-token"
```

Use `token_env` when the token is stored under a different environment-variable
name. Tokens are not accepted directly in the paper config.

## Configuration

```json
{
  "type": "readwise",
  "token_env": "READWISE_TOKEN",
  "limit": 5,
  "since_days_ago": 2,
  "location": "later",
  "category": "article",
  "tags": ["morning", "longform"],
  "body_source": "text"
}
```

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `token_env` | No | `READWISE_TOKEN` | Non-empty name of the environment variable containing the API token. |
| `limit` | No | `5` | Positive configured document limit. The library API also honors a lower limit supplied by its caller. |
| `since_days_ago` | No | No cutoff | A positive value requests documents updated within this many days; `0` behaves like omission. |
| `location` | No | `later` | `new`, `later`, `shortlist`, `archive`, `feed`, or `null` for no location filter. |
| `category` | No | `article` | One of the supported Reader categories, or `null` for no category filter. |
| `tags` | No | `[]` | Array of non-empty tag names sent to the Reader API. |
| `body_source` | No | `text` | `text`, `html`, or `summary`; see below. |

## Body selection

- `text` extracts block text from the document HTML, drops script-like elements,
  and falls back to the summary.
- `html` removes forms, scripts, styles, SVG, and similar elements from the document
  HTML, then falls back to the summary.
- `summary` uses only the Reader summary.

Supported categories are `article`, `email`, `rss`, `highlight`, `note`, `pdf`,
`epub`, `tweet`, and `video`.

Child documents and documents with no usable body are skipped. The provider follows
Reader pagination until it reaches its effective limit or the API has no next page.
