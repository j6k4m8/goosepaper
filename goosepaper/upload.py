from goosepaper.multiparser import MultiParser
from rmapy.document import ZipDocument
from rmapy.api import Folder

import os
from pathlib import Path

from .auth import auth_client


def sanitycheck(folder: str, client):

    # First lets do a sanity check. Since RM cloud uses an object ID as a unique key
    # it is entirely possible to have duplicate VissibleName attributes for both folders and
    # documents, and you can have folders and documents that share the same name.

    # This is insanity and we have no programmatic way to resolve it so we're going to cheat.
    # Check for duplicate folder names as the root level and if found we simply force the
    # user to resolve it and check for duplicate document names.

    rootfolders = [
        f
        for f in client.get_meta_items()
        if (f.Type == "CollectionType" and f.Parent == "")
    ]

    uniquefolders = set()
    [
        uniquefolders.add(folder.VissibleName.lower()) or folder
        for folder in rootfolders
        if folder.VissibleName.lower() not in uniquefolders
    ]
    foldercountdif = abs(len(uniquefolders) - len(rootfolders))

    folderduperr = ""

    if foldercountdif == 1:
        folderduperr = "I found a duplicate folder name in the root of your RM.\n"
    elif foldercountdif > 1:
        folderduperr = (
            "You have multiple duplicate folder names in the root of your RM.\n"
        )
    else:
        pass

    if foldercountdif:
        print("{0}\n\nYou must fix this first.".format(folderduperr))
        return False
    else:
        return True


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


def getallitems(client):

    # So somehow I corrupted or broke my cloud during testing and any object
    # which exists is getting returned twice in the object list from
    # get_meta_items. Deleting items and re-adding them hasn't fixed it even
    # using the official RM client. So this avoids that problem. I haven't found
    # a real fix yet for my cloud though.

    allitems = [item for item in client.get_meta_items() if (item.Parent != "trash")]

    items = []
    for tempitem in allitems:
        if not any(item.ID == tempitem.ID for item in items):
            items.append(tempitem)

    return items


def upload(filepath, multiparser=None):

    if not multiparser:
        multiparser = MultiParser()

    filepath = Path(filepath)
    replace = (
        False
        if multiparser.argumentOrConfig("noreplace")
        else multiparser.argumentOrConfig("replace")
    )
    folder = multiparser.argumentOrConfig("folder")
    cleanup = multiparser.argumentOrConfig("cleanup")
    strictlysane = multiparser.argumentOrConfig("strictlysane")
    nocase = multiparser.argumentOrConfig("nocase")

    if strictlysane:
        nocase = True

    if multiparser.argumentOrConfig("showconfig"):
        print("\nParameters passed to upload\n----------------\n")
        print(
            "Replace:\t{0}\nFolder:\t\t{1}\nCleanup:\t{2}"
            "\nStrictlysane:\t{3}\nNocase:\t\t{4}\nFilepath:\t{5}\n".format(
                replace, folder, cleanup, strictlysane, nocase, filepath
            )
        )

    client = auth_client()

    if not client:
        print("Honk Honk! Couldn't auth! Is your rmapy configured?")
        return False

    if not validateFolder(folder):
        return False

    # Added error handling to deal with possible race condition where the file
    # is mangled or not written out before the upload actually occurs such as
    # an AV false positive. 'pdf' is a simple throwaway file handle to make
    # sure that we retain control of the file while it's being imported.

    fpr = filepath.resolve()

    try:
        doc = ZipDocument(doc=str(fpr))
    except IOError as err:
        raise IOError(f"Error locating or opening {filepath} during upload.") from err

    paperCandidates = []
    paperFolder = None

    for item in getallitems(client):

        # is it the folder we are looking for?
        if (
            folder
            and item.Type == "CollectionType"  # is a folder
            and item.VissibleName.lower()
            == folder.lower()  # has the name we're looking for
            and (item.Parent is None or item.Parent == "")
        ):  # is not in another folder
            paperFolder = item

        # is it possibly the file we are looking for?
        elif item.Type == "DocumentType" and (
            item.VissibleName.lower() == str(doc.metadata["VissibleName"]).lower()
        ):
            paperCandidates.append(item)

    # TODO: if the folder was found, check if a paper candidate is in it
    # for paper in paperCandidates:
    #     parent = client.get_doc(paper.Parent)

    paper = None
    if len(paperCandidates) > 0:
        if folder:
            filtered = [
                item for item in paperCandidates if item.Parent == paperFolder.ID
            ]
        else:
            filtered = list(
                filter(
                    lambda item: item.Parent != "trash"
                    and client.get_doc(item.Parent) is None,
                    paperCandidates,
                )
            )

        if len(filtered) > 1 and replace:
            print(
                "multiple candidate papers with the same name "
                f"{filtered[0].VissibleName}, don't know which to delete"
            )
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

    # workarround rmapy bug: client.upload(doc) would set a non-existing parent
    # ID to the document
    if not paperFolder:
        paperFolder = Folder()
        paperFolder.ID = ""
    if isinstance(paperFolder, Folder):
        result = client.upload(doc, paperFolder)
        if result:
            print("Honk! Upload successful!")
            if cleanup:
                try:
                    os.remove(fpr)
                except Exception as err:
                    raise IOError(f"Failed to remove file after upload: {fpr}") from err
        else:
            print("Honk! Error with upload!")
        return result
    else:
        print("Honk! Could not upload: Document already exists.")
    return False
