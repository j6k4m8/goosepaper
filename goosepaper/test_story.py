from .story import Story


def test_headline_visible_defaults_to_true():
    story = Story("Headline", body_text="body")
    assert story.headline_visible is True


def test_to_html_renders_the_headline_by_default():
    story = Story("Headline", body_text="body")
    assert "<h1 class='story-headline " in story.to_html()
    assert "Headline" in story.to_html()


def test_to_html_omits_the_headline_when_headline_visible_is_false():
    story = Story("Headline", body_text="body", headline_visible=False)
    html = story.to_html()
    assert "<h1" not in html
    # The headline text itself must not leak into the body some other way either.
    assert "Headline" not in html


def test_headline_visible_false_still_keeps_the_headline_text_and_anchor():
    """headline_visible only controls the rendered tag - the text itself stays available for
    everything else that reads it directly (table-of-contents entries, anchor-id slugging,
    deduplicate=True's headline-based matching)."""
    story = Story("Headline", body_text="body", headline_visible=False)
    assert story.headline == "Headline"
    assert 'id="my-anchor"' in story.to_html(anchor_id="my-anchor")
