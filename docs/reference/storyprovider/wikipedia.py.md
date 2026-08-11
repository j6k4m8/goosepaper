# Wikipedia current events

The `wikipedia` source adds today's current-events digest as one story.

## Configuration

```json
{
  "type": "wikipedia"
}
```

This source has no additional configuration fields. Unknown fields are rejected by
the paper-config parser.

The provider reads the current-events feed from
`https://www.to-rss.xyz/wikipedia/current_events/`, removes nested list markup from
links, and renders the digest under the headline `Today's Current Events`. It needs
network access and returns no story when the feed is empty.
