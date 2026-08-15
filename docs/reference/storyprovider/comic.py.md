# Daily comic strips

The `comic` source downloads today's strip of a daily comic and embeds it as a single
image story: `xkcd`, or any comic hosted on gocomics.com or arcamax.com.

## Configuration

```json
{ "type": "comic", "comic_type": "xkcd" }
```

```json
{ "type": "comic", "comic_type": "gocomics", "comic_name": "calvinandhobbes" }
```

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `comic_type` | Yes | — | `xkcd`, `gocomics`, or `arcamax`. No default on purpose - a config that forgets it fails loudly instead of silently always fetching XKCD. |
| `comic_name` | Required for `gocomics`/`arcamax`, rejected for `xkcd` | — | The comic's own slug on that site, exactly as it appears in the site's URL - e.g. `garfield` or `calvinandhobbes` for gocomics.com, `beetlebailey` for arcamax.com. |

## Sites

`gocomics.com` and `arcamax.com` each host hundreds of comics under one identical URL
scheme, so any comic on either site works just by giving its slug as `comic_name` - no
code change or per-comic entry needed. `xkcd` only ever serves one comic and takes no
`comic_name`.

- `xkcd`: headline is fixed to `XKCD`. The strip's real per-day title is still available
  via the embedded image's `alt` attribute, and its mouseover joke still renders as a
  caption under the image.
- `gocomics`: the headline is read off each fetched page's own structured `ComicSeries`
  metadata, so any `comic_name` on the site works without a hardcoded label list.
  gocomics.com requires browser-like request headers, sent automatically. Its page URL
  is date-scoped (`.../<comic_name>/YYYY/MM/DD`); if the requested day's strip isn't
  published yet, it automatically retries a few days back instead of failing outright -
  logged when that happens, nothing shows up differently in the newspaper itself.
- `arcamax`: the headline is likewise read off each fetched page (its `og:title` meta
  tag). No title/caption is otherwise available on the source page.

Every story's headline is a fixed, source-derived name - never the strip's own per-day
title - and no byline is set: a byline or dynamic per-day headline would just repeat the
same source name the headline already shows, unlike a byline on an RSS article (which
distinguishes otherwise-anonymous entries pulled from different feeds).

The strip image itself is left as a plain remote link - this source only resolves which
URL is the actual strip. Fetching it, bounding its pixel dimensions, normalizing color
mode (handling CMYK source JPEGs), compositing any transparency onto white, and inlining
it as a self-contained base64 `data:` URI all happen centrally when the paper is
rendered, the same way for every source's images, not just comics.
