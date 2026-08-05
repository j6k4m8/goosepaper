import argparse
import json
import os
from pathlib import Path
from typing import Optional

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


def _list_active_items(client, refresh: bool = False):
    return [item for item in client.list_items(refresh=refresh) if item.parent != "trash"]


def _apply_retention(client, parent_id: str, prefix: str, keep_last_n: int) -> None:
    """Deletes older documents in the same folder as the just-uploaded one, keeping only the
    `keep_last_n` most recent whose name starts with `prefix` - for a paper delivered on a
    schedule under a name like "Daily Goose 2026-08-05", `prefix` would be "Daily Goose " so this
    matches every dated edition of that same paper (and nothing else sharing the folder).

    Always passes refresh=True to list_items() here, deliberately not reusing whatever was
    already listed to resolve the folder/replace target above: Client.list_items() caches the
    root state and only re-fetches it when asked, and while put_pdf()/put_epub() (used whenever
    a folder is involved, i.e. exactly when retention is usable at all) do refresh that cache via
    their own refresh=True, upload_pdf()/upload_epub() (the plain root-level path) do not - so an
    unqualified list_items() call here could silently read stale, pre-upload state depending on
    which upload path just ran. Forcing refresh=True removes that as something to reason about,
    at the cost of one guaranteed extra API round-trip.
    """
    editions = sorted(
        (
            item
            for item in _list_active_items(client, refresh=True)
            if item.type == "DocumentType"
            and item.parent == parent_id
            and item.visibleName.startswith(prefix)
        ),
        key=lambda item: item.visibleName,
        reverse=True,
    )
    for stale in editions[keep_last_n:]:
        client.delete(stale.id, refresh=True)


def upload(
    filepath,
    delivery_settings: Optional[DeliverySettings] = None,
    showconfig=False,
    interactive: bool = True,
):
    filepath = Path(filepath)
    delivery = _coerce_delivery_settings(delivery_settings)

    replace = delivery.replace_mode in {"exact", "nocase"}
    nocase = delivery.replace_mode == "nocase"
    folder = delivery.folder
    cleanup = delivery.cleanup

    if showconfig:
        print(json.dumps(delivery.to_dict(), indent=2))

    client = auth_client(interactive=interactive)

    if not client:
        print("Honk Honk! Couldn't auth! Is your remarkapy config set up (~/.rmapi)?")
        return False

    fpr = filepath.resolve()
    if not fpr.exists():
        raise IOError(f"Error locating or opening {filepath} during upload.")

    target_name = _name_for_matching(filepath.stem, nocase)
    payload = fpr.read_bytes()
    suffix = fpr.suffix.lower()

    paper_candidates = []
    folder_candidates = []
    needs_library_scan = bool(folder) or replace

    if needs_library_scan:
        for item in _list_active_items(client):
            if (
                folder
                and item.type == "CollectionType"
                and _name_for_matching(item.visibleName, nocase)
                == _name_for_matching(folder, nocase)
                and item.parent == ""
            ):
                folder_candidates.append(item)
            elif replace and item.type == "DocumentType" and (
                _name_for_matching(item.visibleName, nocase) == target_name
            ):
                paper_candidates.append(item)

    if len(folder_candidates) > 1:
        print(f"multiple candidate folders with the same name {folder}")
        return False
    paper_folder = folder_candidates[0] if folder_candidates else None

    if folder:
        filtered = [
            item
            for item in paper_candidates
            if paper_folder is not None and item.parent == paper_folder.id
        ]
    else:
        filtered = [item for item in paper_candidates if item.parent == ""]

    if filtered:
        if not replace:
            print("Honk! The paper already exists!")
            return False
        if len(filtered) > 1:
            print(
                "multiple candidate papers with the same name "
                f"{filtered[0].visibleName}, don't know which to delete"
            )
            return False
        client.delete(filtered[0].id, refresh=True)

    parent_id = ""
    if folder and not paper_folder:
        paper_folder = client.put_folder(folder, refresh=True)
        parent_id = paper_folder.id
    elif paper_folder:
        parent_id = paper_folder.id

    if suffix not in {".pdf", ".epub"}:
        raise ValueError("Only PDF and EPUB uploads are supported.")

    result = _upload_document(
        client,
        visible_name=filepath.stem,
        payload=payload,
        suffix=suffix,
        parent_id=parent_id,
    )

    if result is not None:
        print("Honk! Upload successful!")
        if delivery.retention_keep_last_n is not None:
            _apply_retention(
                client, parent_id, delivery.retention_prefix, delivery.retention_keep_last_n
            )
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
        "--retention-keep-last-n",
        type=int,
        required=False,
        help='Keep only the last N delivered documents whose name starts with '
        '"--retention-prefix", deleting older ones. Requires "--retention-prefix".',
    )
    parser.add_argument(
        "--retention-prefix",
        required=False,
        help='The name prefix "--retention-keep-last-n" matches past editions against. '
        'Requires "--retention-keep-last-n".',
    )
    parser.add_argument(
        "--showconfig",
        action="store_true",
        required=False,
        help="Print the resolved delivery settings before uploading.",
    )
    parser.add_argument(
        "--no-interactive",
        dest="interactive",
        action="store_false",
        default=True,
        help="Fail with a clean error instead of prompting for reMarkable pairing if no device "
        "token is configured. For unattended use (cron, CI) where there's no terminal to prompt.",
    )
    parsed = parser.parse_args(args)

    try:
        delivery = resolve_delivery_settings(
            user_defaults=load_user_config().delivery_defaults,
            folder_override=parsed.folder,
            replace_mode_override=parsed.replace_mode,
            cleanup_override=parsed.cleanup,
            retention_keep_last_n_override=parsed.retention_keep_last_n,
            retention_prefix_override=parsed.retention_prefix,
        )
    except ConfigError as err:
        print(f"Honk! {err}")
        return 1

    result = upload(
        parsed.filepath,
        delivery_settings=delivery,
        showconfig=parsed.showconfig,
        interactive=parsed.interactive,
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


def _upload_document(client, visible_name: str, payload: bytes, suffix: str, parent_id: str):
    if parent_id == "":
        if suffix == ".pdf":
            return client.upload_pdf(visible_name, payload)
        if suffix == ".epub":
            return client.upload_epub(visible_name, payload)
        raise ValueError("Only PDF and EPUB uploads are supported.")

    if suffix == ".pdf":
        return client.put_pdf(visible_name, payload, parent=parent_id, refresh=True)
    if suffix == ".epub":
        return client.put_epub(visible_name, payload, parent=parent_id, refresh=True)
    raise ValueError("Only PDF and EPUB uploads are supported.")
