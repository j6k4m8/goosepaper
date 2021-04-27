import sys
import datetime

from goosepaper.goosepaper import Goosepaper
from goosepaper.util import construct_story_providers_from_config_dict
from goosepaper.upload import upload
from goosepaper.multiparser import MultiParser


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
    folder = multiparser.argumentOrConfig("folder", None)

    paper = Goosepaper(story_providers=story_providers, title=title, subtitle=subtitle)

    if filename.endswith(".html"):
        with open(filename, "w") as fh:
            fh.write(paper.to_html())
    elif filename.endswith(".pdf"):
        paper.to_pdf(filename)
    elif filename.endswith(".epub"):
        paper.to_epub(filename)
    else:
        raise ValueError(f"Unknown file extension '{filename.split('.')[-1]}'.")

    if multiparser.argumentOrConfig("upload", folder):
        upload(filename, replace, folder)

    return 0

if __name__ == "__main__":
    sys.exit(main())
