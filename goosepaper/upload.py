import argparse
import json
import os
from pathlib import Path
from typing import Optional

from rmapy.api import Folder
from rmapy.document import ZipDocument

from .auth import auth_client
from .config import (
    ConfigError,
    DeliverySettings,
    REPLACE_MODES,
    load_user_config,
    resolve_delivery_settings,
)


def _name_for_matching(value: str, nocase: bool) -> str:
    return value.lower() if nocase else value


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


def upload(filepath, delivery_settings: Optional[DeliverySettings] = None, showconfig=False):
    filepath = Path(filepath)
    delivery = _coerce_delivery_settings(delivery_settings)

    replace = delivery.replace_mode in {"exact", "nocase"}
    nocase = delivery.replace_mode == "nocase"
    folder = delivery.folder
    cleanup = delivery.cleanup

    if showconfig:
        print(json.dumps(delivery.to_dict(), indent=2))

    client = auth_client()

    if not client:
        print("Honk Honk! Couldn't auth! Is your rmapy configured?")
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
    target_name = _name_for_matching(str(doc.metadata["VissibleName"]), nocase)

    paper_candidates = []
    paper_folder = None

    for item in getallitems(client):
        if (
            folder
            and item.Type == "CollectionType"
            and _name_for_matching(item.VissibleName, nocase)
            == _name_for_matching(folder, nocase)
            and (item.Parent is None or item.Parent == "")
        ):
            paper_folder = item
        elif item.Type == "DocumentType" and (
            _name_for_matching(item.VissibleName, nocase) == target_name
        ):
            paper_candidates.append(item)

    paper = None
    if paper_candidates:
        if folder:
            filtered = (
                [item for item in paper_candidates if item.Parent == paper_folder.ID]
                if paper_folder
                else []
            )
        else:
            filtered = [
                item
                for item in paper_candidates
                if item.Parent != "trash" and client.get_doc(item.Parent) is None
            ]

        if len(filtered) > 1 and replace:
            print(
                "multiple candidate papers with the same name "
                f"{filtered[0].VissibleName}, don't know which to delete"
            )
            return False
        if len(filtered) == 1:
            paper = filtered[0]

    if paper is not None:
        if replace:
            client.delete(paper)
        else:
            print("Honk! The paper already exists!")
            return False

    if folder and not paper_folder:
        paper_folder = Folder(folder)
        if not client.create_folder(paper_folder):
            print("Honk! Failed to create the folder!")
            return False

    # workaround rmapy bug: client.upload(doc) would set a non-existing parent
    # ID to the document
    if not paper_folder:
        paper_folder = Folder()
        paper_folder.ID = ""

    result = client.upload(doc, paper_folder)
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


def main(args=None):
    parser = argparse.ArgumentParser(
        prog="upload_to_remarkable",
        description="Upload an existing PDF or EPUB to your reMarkable.",
    )
    parser.add_argument("filepath", help="The existing file to upload.")
    parser.add_argument("-f", "--folder", required=False)
    parser.add_argument("--replace-mode", choices=REPLACE_MODES, required=False)
    cleanup_group = parser.add_mutually_exclusive_group()
    cleanup_group.add_argument(
        "--cleanup",
        dest="cleanup",
        action="store_true",
        default=None,
    )
    cleanup_group.add_argument(
        "--no-cleanup",
        dest="cleanup",
        action="store_false",
        default=None,
    )
    parser.add_argument(
        "--showconfig",
        action="store_true",
        required=False,
        help="Print the resolved delivery settings before uploading.",
    )
    parsed = parser.parse_args(args)

    try:
        delivery = resolve_delivery_settings(
            user_defaults=load_user_config().delivery_defaults,
            folder_override=parsed.folder,
            replace_mode_override=parsed.replace_mode,
            cleanup_override=parsed.cleanup,
        )
    except ConfigError as err:
        print(f"Honk! {err}")
        return 1

    result = upload(
        parsed.filepath,
        delivery_settings=delivery,
        showconfig=parsed.showconfig,
    )
    return 0 if result else 1


def _coerce_delivery_settings(
    delivery_settings: Optional[DeliverySettings],
) -> DeliverySettings:
    if delivery_settings is None:
        return load_user_config().delivery_defaults
    if isinstance(delivery_settings, DeliverySettings):
        return delivery_settings
    if isinstance(delivery_settings, dict):
        return DeliverySettings(**delivery_settings)
    raise TypeError(
        "delivery_settings must be a DeliverySettings instance, a dict, or None."
    )
