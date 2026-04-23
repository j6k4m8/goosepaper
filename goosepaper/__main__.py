import sys

from goosepaper.goosepaper import Goosepaper
from goosepaper.config import ConfigError, dump_resolved_config, resolve_runtime_config
from goosepaper.upload import upload
from goosepaper.util import construct_story_providers_from_source_configs


def main(args=None):
    try:
        config = resolve_runtime_config(args)
    except ConfigError as err:
        print(f"Honk! {err}")
        return 1

    if config.showconfig:
        print(dump_resolved_config(config))

    if not config.nostory:
        story_providers = construct_story_providers_from_source_configs(config.sources)
        paper = Goosepaper(
            story_providers=story_providers,
            title=config.paper.title,
            subtitle=config.paper.subtitle,
        )

        if config.output.endswith(".html"):
            with open(config.output, "w", encoding="utf-8") as fh:
                fh.write(paper.to_html())
        elif config.output.endswith(".pdf"):
            paper.to_pdf(
                config.output,
                font_size=config.paper.font_size,
                style=config.paper.style,
            )
        elif config.output.endswith(".epub"):
            paper.to_epub(
                config.output,
                font_size=config.paper.font_size,
                style=config.paper.style,
            )
        else:
            print(f"Unknown file extension '{config.output.split('.')[-1]}'.")
            return 1

    if config.deliver:
        upload(filepath=config.output, delivery_settings=config.delivery)

    return 0


if __name__ == "__main__":
    sys.exit(main())
