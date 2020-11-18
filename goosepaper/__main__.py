import sys
import argparse
import datetime

from goosepaper.goosepaper import Goosepaper
from goosepaper.util import (
    construct_story_providers_from_config_dict,
    load_config_file )


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
        default=f"Goosepaper-{datetime.datetime.now().strftime('%Y-%B-%d-%H-%M')}.pdf",
        help="The output file path at which to save the paper",
    )

    args = parser.parse_args()

    try:
        config = load_config_file(args.config)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Could not find the configuration file at {args.config}"
        ) from e

    story_providers = construct_story_providers_from_config_dict(config)

    paper = Goosepaper(story_providers=story_providers)

    if args.output.endswith(".html"):
        with open(args.output, "w") as fh:
            fh.write(paper.to_html())
    elif args.output.endswith(".pdf"):
        paper.to_pdf(args.output)
    elif args.output.endswith(".epub"):
        paper.to_epub(args.output)
    else:
        raise ValueError(f"Unknown file extension '{args.output.split('.')[-1]}'.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())