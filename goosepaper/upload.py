import argparse
from pathlib import Path

from rmapy.document import ZipDocument
from rmapy.api import Client, Folder
from rmapy.exceptions import AuthError

def validateFolder(folder: str):
    if folder:
        if folder == "":
            print("Honk! Folder cannot be an empty string")
            return False
        elif "/" in folder:
            print("Honk! Please do not include '/' in the folder name")
            print("      Nested folders are not supported for now")
            return False

    return True

def upload(filepath=None, replace=False, folder=None):

    if not filepath:
        parser = argparse.ArgumentParser("Upload Goosepaper to reMarkable tablet")
        parser.add_argument(
            "file", default=None, help="The file to upload",
        )
        args = parser.parse_args()
        filepath = args.file

    filepath = Path(filepath)

    client = Client()

    try:
        client.renew_token()
    except AuthError:
        print(
            "Looks like this if the first time you've uploaded, need to register the device"
        )
        print("Get the code from here: https://my.remarkable.com/connect/remarkable")
        code = input()
        print("registering")
        client.register_device(code)
        if not client.renew_token():
            print("registration failed D:")
        else:
            print("registration successful")

    if not validateFolder(folder):
        return False

    paperCandidates = []
    paperFolder = None

    items = client.get_meta_items()
    for item in items:
        # is it the folder we are looking for?
        if (folder and item.Type == "CollectionType"              # is a folder
                and item.VissibleName == folder                   # has the name we're looking for
                and (item.Parent == None or item.Parent == "")):  # is not in another folder
            paperFolder = item

        # is it possibly the file we are looking for?
        elif item.Type == "DocumentType" and item.VissibleName == filepath.stem:
            paperCandidates.append(item)

    for paper in paperCandidates:
        if paper.Parent == "trash":
            continue
        parent = client.get_doc(paper.Parent)

    # if the folder was found, check if a paper candidate is in it
    paper = None
    if len(paperCandidates) > 0:
        if folder:
            filtered = list(filter(lambda item: item.Parent == paperFolder.ID, paperCandidates))
        else:
            filtered = list(filter(lambda item: item.Parent != "trash"
                                   and client.get_doc(item.Parent) == None,
                                   paperCandidates))

        if len(filtered) > 1 and replace:
            print(f"multiple candidate papers with the same name {filtered[0].VissibleName}, don't know which to delete")
            return False
        if len(filtered) == 1:  # found the outdated paper
            paper = filtered[0]

    if paper is not None:
        if replace:
            result = client.delete(paper)
        else:
            print("Honk! The paper already exists!")
            return False

    if folder and not paperFolder:
        paperFolder = Folder(folder)
        if not client.create_folder(paperFolder):
                print("Honk! Failed to create the folder!")
                return False

    doc = ZipDocument(doc=str(filepath.resolve()))
    # workarround rmapy bug: client.upload(doc) would set a non-existing parent ID to the document
    if not paperFolder:
        paperFolder = Folder()
        paperFolder.ID = ""
    result = client.upload(doc, paperFolder)
    if result:
        print("Honk! Upload successful!")
    else:
        print("Honk! Error with upload!")

    return result
