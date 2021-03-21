import sys
import argparse
import datetime

from goosepaper.goosepaper import Goosepaper
from goosepaper.util import (
    construct_story_providers_from_config_dict,
    load_config_file,
)
from goosepaper.upload import upload


def main():
    parser = argparse.ArgumentParser(
        "Goosepaper generates and delivers a daily newspaper in PDF format."
    )
    parser.add_argument(
        "-c",
        "--config",
        required=False,
        default=None,
        help="The json file to use to generate this paper.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        help="The output file path at which to save the paper",
    )
    parser.add_argument(
        "-u",
        "--upload",
        action="store_true",
        required=False,
        help="Whether to upload the file to your remarkable using rmapy.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        required=False,
        help="Will replace a document with same name in your remarkable.",
    )

    args = parser.parse_args()

    try:
        config = load_config_file(args.config)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Could not find the configuration file at {args.config}"
        ) from e

    story_providers = construct_story_providers_from_config_dict(config)
    title = config["title"] if "title" in config else None
    subtitle = config["subtitle"] if "subtitle" in config else None
    if args.output:
        filename = args.output
    elif "filename" in config:
           filename = config["filename"]
    else:
        filename = f"Goosepaper-{datetime.datetime.now().strftime('%Y-%B-%d-%H-%M')}.pdf"
    if args.replace:
        if not args.upload:
            parser.error("--replace requires --upload.")
        replace = args.replace
    elif "replace" in config:
        replace = config["replace"]
    else:
        replace = False

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

    if args.upload:
        upload(filename, replace)

    return 0


if __name__ == "__main__":
    sys.exit(main())
