import sys
import datetime

from goosepaper.goosepaper import Goosepaper
from goosepaper.util import StoryPriority, construct_story_providers_from_config_dict, write_config_file
from goosepaper.upload import upload
from goosepaper.multiparser import MultiParser
from functools import reduce
from .util import PlacementPreference


def main():
    multiparser = MultiParser()
    config = multiparser.config

    story_providers = construct_story_providers_from_config_dict(config)

    title = config["title"] if "title" in config else None
    subtitle = config["subtitle"] if "subtitle" in config else None
    filename = multiparser.argumentOrConfig(
        "output",
        default=f"Goosepaper-{datetime.datetime.now().strftime('%Y-%B-%d-%H-%M')}.pdf"
    )
    replace = multiparser.argumentOrConfig("replace", False)
    last_updated = multiparser.argumentOrConfig("last_updated")

    paper = Goosepaper(story_providers=story_providers, title=title, subtitle=subtitle)
    stories = paper.get_stories(since=last_updated)
    if len(stories) == 0 or (len(stories) == 1 and stories[0].placement_preference == PlacementPreference.EAR):
        print("Honk! No new stories!")
        return 0

    if filename.endswith(".html"):
        with open(filename, "w") as fh:
            fh.write(paper.to_html(stories))
    elif filename.endswith(".pdf"):
        paper.to_pdf(stories, filename)
    elif filename.endswith(".epub"):
        paper.to_epub(filename)
    else:
        raise ValueError(f"Unknown file extension '{filename.split('.')[-1]}'.")

    if multiparser.argumentOrConfig("upload"):
        upload(filename, replace)

    last_updated = reduce(lambda a, b:  a if a > b else b, stories).date
    if last_updated:
        config["last_updated"] = str(last_updated)
        write_config_file(multiparser.argumentOrConfig("config"), config)

    return 0

if __name__ == "__main__":
    sys.exit(main())
