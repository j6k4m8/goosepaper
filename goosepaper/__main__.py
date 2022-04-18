import sys
import datetime

from goosepaper.goosepaper import Goosepaper
from goosepaper.util import construct_story_providers_from_config_dict
from goosepaper.upload import upload
from goosepaper.multiparser import MultiParser


def main():
    multiparser = MultiParser()
    config = multiparser.config

    nostory = multiparser.argumentOrConfig("nostory")

    filename = multiparser.argumentOrConfig(
        "output",
        default=f"Goosepaper-{datetime.datetime.now().strftime('%Y-%B-%d-%H-%M')}.pdf",
    )
    replace = multiparser.argumentOrConfig("replace", False)
    folder = multiparser.argumentOrConfig("folder", None)
    font_size = multiparser.argumentOrConfig("font_size", 14)

    if not nostory:  # global nostory flag
        story_providers = construct_story_providers_from_config_dict(config)
        font_size = multiparser.argumentOrConfig("font_size", 14)
        style = multiparser.argumentOrConfig("style", "FifthAvenue")

        title = config["title"] if "title" in config else None
        subtitle = config["subtitle"] if "subtitle" in config else None

        paper = Goosepaper(
            story_providers=story_providers, title=title, subtitle=subtitle
        )

        if filename.endswith(".html"):
            with open(filename, "w") as fh:
                fh.write(paper.to_html())
        elif filename.endswith(".pdf"):
            paper.to_pdf(filename, font_size=font_size, style=style)
        elif filename.endswith(".epub"):
            paper.to_epub(filename, font_size=font_size, style=style)
        else:
            print(f"Unknown file extension '{filename.split('.')[-1]}'.")
            exit(1)

    if multiparser.argumentOrConfig("upload"):
        if multiparser.argumentOrConfig("noupload"):
            print(
                "Honk! The 'upload' directive was found, but '--noupload' was also specified on the command line. Your goosepaper {0} was generated but I'm not uploading it.".format(
                    filename
                )
            )
        else:
            upload(filepath=filename, multiparser=multiparser)

    return 0


if __name__ == "__main__":
    sys.exit(main())
