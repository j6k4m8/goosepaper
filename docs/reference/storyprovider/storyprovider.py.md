# Custom text stories

Use the `text` source when a paper needs fixed prose alongside fetched stories. It
creates the requested number of identical stories and does not make a network
request.

## Configuration

```json
{
  "type": "text",
  "headline": "Good morning",
  "text": "Remember to water the plants.",
  "limit": 1
}
```

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `headline` | No | `Lorem Ipsum Dolor Sit Amet` | Non-empty headline used for every generated story. |
| `text` | No | Built-in lorem ipsum | Non-empty plain-text body used for every generated story. |
| `limit` | No | `5` | Positive number of copies to generate. |

The config type maps to `CustomTextStoryProvider`. `LoremStoryProvider` remains an
alias for library users.

## Writing a custom provider

A story provider implements `get_stories()` and returns a list of `Story` objects.
Library integrations can call the exported `register_story_provider()` helper with
a config type, provider class, required and optional field names, and an optional
normalizer. Registered types then work in the same `sources` array as the built-in
providers.
