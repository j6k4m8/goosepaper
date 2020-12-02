import argparse
from pathlib import Path

from rmapy.document import ZipDocument
from rmapy.api import Client
from rmapy.exceptions import AuthError


def upload(filepath=None):

    if not filepath:
        parser = argparse.ArgumentParser(
            "Upload Goosepaper to reMarkable tablet"
        )
        parser.add_argument(
            "file",
            default=None,
            help="The file to upload",
        )
        args = parser.parse_args()
        filepath = args.file
    filepath = Path(filepath)

    client = Client()

    try:
        client.renew_token()
    except AuthError:
        print(
            "Looks like this if the first time you've uploaded, need to register the device")
        print("Get the code from here: https://my.remarkable.com/connect/remarkable")
        code = input()
        print("registering")
        client.register_device(code)
        if not client.renew_token():
            print("registration failed D:")
        else:
            print("registration successful")

    for item in client.get_meta_items():
        if item.VissibleName == filepath.stem:
            print("Honk! Paper already exists!")
            return True

    doc = ZipDocument(doc=str(filepath.resolve()))
    if client.upload(doc):
        print("Honk! Upload successful!")
    else:
        print("Honk! Error with upload!")

    return True
