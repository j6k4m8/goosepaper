import argparse

from goosepaper.util import load_config_file

class MultiParser:
    def __init__(self):
        """
        Creates a new MultiParser, which abstracts acessing command line arguments and config
        file entries.

        """

        self.parser = argparse.ArgumentParser(
            prog="goosepaper",
            description="Goosepaper generates and delivers a daily newspaper in PDF format."
        )
        self.parser.add_argument(
            "-c",
            "--config",
            required=False,
            default=None,
            help="The json file to use to generate this paper.",
        )
        self.parser.add_argument(
            "-o",
            "--output",
            required=False,
            help="The output file path at which to save the paper",
        )
        self.parser.add_argument(
            "-u",
            "--upload",
            action="store_true",
            required=False,
            help="Whether to upload the file to your remarkable using rmapy.",
        )
        self.parser.add_argument(
            "--replace",
            action="store_true",
            required=False,
            default=None,
            help="Will replace a document with same name in your remarkable.",
        )
        self.parser.add_argument(
            "-f",
            "--folder",
            required=False,
            help="Folder to which the document will be uploaded in your remarkable.",
        )
        self.args = self.parser.parse_args()

        try:
            self.config = load_config_file(self.args.config)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Could not find the configuration file at {self.args.config}"
            ) from e


    def argumentOrConfig(self, key, default=None, dependency=None):
        """
        Returns a command line argument or an entry from the config file

        Arguments:
            key: the command line option name (as in --key) or config file entry
            default (str: None): the default value, returned  if the key was not set both as a 
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
            value = self.config[key]
        else:
            value = default

        return value


