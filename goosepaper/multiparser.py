import argparse
import pathlib

from goosepaper.util import load_config_file


class NewLineFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith("||"):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


class MultiParser:
    def __init__(self):
        """
        Creates a new MultiParser, which abstracts acessing command line arguments and config
        file entries.

        """

        self.parser = argparse.ArgumentParser(
            prog="goosepaper",
            description="Goosepaper generates and delivers a daily newspaper in PDF format.",
            formatter_class=NewLineFormatter,
        )

        self.parser.add_argument(
            "-c",
            "--config",
            required=False,
            default="",
            help="The json file to use to generate this paper.",
        )
        self.parser.add_argument(
            "-o",
            "--output",
            required=False,
            help="The output file path at which to save the paper",
        )
        self.parser.add_argument(
            "-f",
            "--folder",
            required=False,
            help="Folder to which the document will be uploaded in your remarkable.",
        )
        self.parser.add_argument(
            "-u",
            "--upload",
            action="store_true",
            required=False,
            default=None,
            help="Whether to upload the file to your remarkable using rmapy.",
        )
        self.parser.add_argument(
            "--noupload",
            action="store_true",
            required=False,
            default=None,
            help="Overrides any other 'upload: true' arguments from config files or command line. Useful for testing configs or story generation without having to edit config files.",
        )
        self.parser.add_argument(
            "--showconfig",
            action="store_true",
            required=False,
            default=None,
            help="Print out all config files and command line options in order loaded and the final config to help finding conflicting options. Needed since there are now four possible ways to pass options.",
        )
        self.parser.add_argument(
            "-n",
            "--nostory",
            required=False,
            default=False,
            action="store_true",
            help='||Skip story creation. Combined with "--upload" can be used to\nupload a preexisting output file.\n\n** NOTE ** If used without "--upload" goosepaper will run but\nperform no action.',
        )
        self.parser.add_argument(
            "--replace",
            action="store_true",
            required=False,
            default=None,
            help="||Will replace a document with same name in your remarkable.\nDefault behaviour is case sensitive (ala *nix/Mac).\n\ne.g. 'A Flock of RSS Feeds.epub' and 'a flock of rss feeds.epub'\nare seen as TWO different files. Can be altered with '--nocase'\nor '--strictlysane' switches.",
        )
        self.parser.add_argument(
            "--noreplace",
            action="store_true",
            required=False,
            default=None,
            help="Only valid when specified on command line (ignored if present in any config file). Supersedes any config file setting for 'replace: true', thus ensuring that the file will NEVER be overwritten. Will also supersede command line '--replace' if both are specified regardless of order.",
        )
        self.parser.add_argument(
            "--cleanup",
            required=False,
            default=None,
            action="store_true",
            help="Delete the output file after upload.",
        )
        self.args = self.parser.parse_args()

        # These are in order of precedence, low to highest
        #  1. Home directory global configs
        #  2. Local directory from which goosepaper is called
        #  3. Specified on the command line.

        defaultconfigs = [
            str(pathlib.Path("~").expanduser()) + "/.goosepaper.json",
            "./goosepaper.json",
            self.args.config,
        ]
        foundconfig = False
        self.config = {}
        outputcount = 0
        debug_configs = True if self.args.showconfig else None

        # Debug code for troubleshooting config file and cli override issues.
        if debug_configs:
            import pprint

            pp = pprint.PrettyPrinter(indent=3)
            print(
                "Command line arguments received:\n(including default values)\n--------------------------------"
            )
            pp.pprint(self.args)

        # If passed a config file on the command line, assume it's important so fail
        # if not readable.

        if self.args.config:
            try:
                load_config_file(self.args.config)
            except FileNotFoundError:
                print(
                    "Honk! Honk! Somebody stole my egg! Couldn't find config file ({0}) specified on the command line. Aborting migration.".format(
                        self.args.config
                    )
                )
                exit(1)

        for defconfigfile in defaultconfigs:
            try:
                tempconfig = load_config_file(defconfigfile)
                if "output" in tempconfig and "output" in self.config:
                    outputcount = outputcount + 1
                if "stories" in tempconfig and "stories" in self.config:
                    for story in self.config["stories"]:
                        tempconfig["stories"].append(story)

                self.config.update(tempconfig)
                foundconfig = True
                if debug_configs:
                    print(
                        f"\nConfig options found in {defconfigfile}:\n---------------------\n"
                    )
                    pp.pprint(load_config_file(defconfigfile))
            except FileNotFoundError as e:
                pass

        if debug_configs:
            print("\nFinal config values are:\n------------------")
            pp.pprint(self.config)
            print("")

        if foundconfig is not True:
            print(
                "Honk! Honk! Unable to locate a config file. You must have at least one of the following! '$HOME/.goosepaper.json', './goosepaper.json', or a config file specified on the command line."
            )
            exit(1)

        # Not sure if you should able to override the output destination or not.

        # if outputcount > 0:
        #    print ("Honk! Honk! You've specified more than one output destination in your config files. A flying flock can only have one lead goose in a skein. Please resolve this.")
        #    exit(1)
        # if 'output' in self.config and self.args.output:
        #    print ("Honk! Honk! You have both config file and command line output file options. I don't know which flock with which to fly with so I'm not flying anywhere. Please fix.")
        #    exit(1)

        # --noreplace only makes sense to me on the command line, so if present in a config file ignore it.
        # Same with --noupload.

        if "noreplace" in self.config:
            del self.config["noreplace"]
        if "noupload" in self.config:
            del self.config["upload"]

    def argumentOrConfig(self, key, default=None, dependency=None):
        """
        Returns a command line argument or an entry from the config file

        Arguments:
            key: the command line option name (as in --key) or config file entry
            default (str: None): the default value, returned if the key was not set both as a
            command line argument and a config entry
            dependency (str: None): the name of a dependency command line argument or config
            entry that must be present for this call to be valid

        Returns:
            If a command line option with 'key' name was set, returns it. Else, if a config
            entry named 'key' was set, returns it. If none of the previous was returned,
            returns the default value specified by the 'default' argument.

        """

        d = vars(self.args)
        if key in d and d[key] is not None:
            if dependency and (not dependency in d):
                self.parser.error(f"--{key} requires --{dependency}.")
            value = d[key]
        elif key in self.config:
            value = self.config[key] or default
        else:
            value = default

        return value
