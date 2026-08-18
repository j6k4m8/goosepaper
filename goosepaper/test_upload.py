from .config import DeliverySettings
from .upload import upload


class _IndexedItem:
    def __init__(self, item_id: str, visible_name: str, parent: str, item_type: str):
        self.id = item_id
        self.visibleName = visible_name
        self.parent = parent
        self.type = item_type


class _Client:
    def __init__(self):
        self.calls = []
        self._items = []

    def list_items(self, refresh=False):
        self.calls.append(("list_items", refresh))
        return self._items

    def upload_pdf(self, visible_name, payload):
        self.calls.append(("upload_pdf", visible_name, payload))
        return type("Result", (), {"id": "doc-1"})()

    def upload_epub(self, visible_name, payload):
        self.calls.append(("upload_epub", visible_name, payload))
        return type("Result", (), {"id": "doc-1"})()

    def put_pdf(self, visible_name, payload, parent="", refresh=False):
        self.calls.append(("put_pdf", visible_name, payload, parent, refresh))
        return object()

    def put_epub(self, visible_name, payload, parent="", refresh=False):
        self.calls.append(("put_epub", visible_name, payload, parent, refresh))
        return object()

    def put_folder(self, visible_name, parent="", refresh=False):
        self.calls.append(("put_folder", visible_name, parent, refresh))
        return type("Result", (), {"id": "folder-1"})()

    def upload_folder(self, visible_name):
        self.calls.append(("upload_folder", visible_name))
        return type("Result", (), {"id": "folder-1"})()

    def delete(self, item_id, refresh=False):
        self.calls.append(("delete", item_id, refresh))
        return object()

    def move(self, item_id, parent, refresh=False):
        self.calls.append(("move", item_id, parent, refresh))
        return object()


def test_upload_root_pdf_uses_simple_upload_without_listing(monkeypatch, tmp_path):
    client = _Client()
    monkeypatch.setattr("goosepaper.upload.auth_client", lambda **kwargs: client)

    filepath = tmp_path / "paper.pdf"
    filepath.write_bytes(b"%PDF-test")

    result = upload(filepath, DeliverySettings(folder=None, replace_mode="never", cleanup=False))

    assert result is not False
    assert ("upload_pdf", "paper", b"%PDF-test") in client.calls
    assert not any(call[0] == "list_items" for call in client.calls)


def test_upload_defaults_to_interactive_auth(monkeypatch, tmp_path):
    seen = {}
    client = _Client()
    monkeypatch.setattr(
        "goosepaper.upload.auth_client",
        lambda **kwargs: seen.update(kwargs) or client,
    )

    filepath = tmp_path / "paper.pdf"
    filepath.write_bytes(b"%PDF-test")

    upload(filepath, DeliverySettings(folder=None, replace_mode="never", cleanup=False))

    assert seen["interactive"] is True


def test_upload_passes_interactive_false_through_to_auth_client(monkeypatch, tmp_path):
    seen = {}
    client = _Client()
    monkeypatch.setattr(
        "goosepaper.upload.auth_client",
        lambda **kwargs: seen.update(kwargs) or client,
    )

    filepath = tmp_path / "paper.pdf"
    filepath.write_bytes(b"%PDF-test")

    upload(
        filepath,
        DeliverySettings(folder=None, replace_mode="never", cleanup=False),
        interactive=False,
    )

    assert seen["interactive"] is False


def test_upload_with_folder_scans_minimal_index(monkeypatch, tmp_path):
    client = _Client()
    client._items = [_IndexedItem("folder-1", "News", "", "CollectionType")]
    monkeypatch.setattr("goosepaper.upload.auth_client", lambda **kwargs: client)

    filepath = tmp_path / "paper.pdf"
    filepath.write_bytes(b"%PDF-test")

    result = upload(filepath, DeliverySettings(folder="News", replace_mode="never", cleanup=False))

    assert result is not False
    assert ("list_items", False) in client.calls
    assert ("put_pdf", "paper", b"%PDF-test", "folder-1", True) in client.calls


def test_upload_with_new_folder_uses_put_folder_and_nested_put_pdf(monkeypatch, tmp_path):
    client = _Client()
    monkeypatch.setattr("goosepaper.upload.auth_client", lambda **kwargs: client)

    filepath = tmp_path / "paper.pdf"
    filepath.write_bytes(b"%PDF-test")

    result = upload(filepath, DeliverySettings(folder="News", replace_mode="never", cleanup=False))

    assert result is not False
    assert ("put_folder", "News", "", True) in client.calls
    assert ("put_pdf", "paper", b"%PDF-test", "folder-1", True) in client.calls


def test_upload_retention_deletes_older_editions_beyond_keep_last_n(monkeypatch, tmp_path):
    client = _Client()
    client._items = [
        _IndexedItem("folder-1", "News", "", "CollectionType"),
        _IndexedItem("doc-2026-08-03", "Daily Goose 2026-08-03", "folder-1", "DocumentType"),
        _IndexedItem("doc-2026-08-04", "Daily Goose 2026-08-04", "folder-1", "DocumentType"),
        _IndexedItem("doc-2026-08-05", "Daily Goose 2026-08-05", "folder-1", "DocumentType"),
        # A different paper sharing the same folder - must never be touched by this paper's
        # retention, since its name doesn't start with the "Daily Goose " prefix.
        _IndexedItem("doc-other", "Weekly Roundup 2026-08-05", "folder-1", "DocumentType"),
    ]
    monkeypatch.setattr("goosepaper.upload.auth_client", lambda **kwargs: client)

    filepath = tmp_path / "Daily Goose 2026-08-06.pdf"
    filepath.write_bytes(b"%PDF-test")

    result = upload(
        filepath,
        DeliverySettings(
            folder="News",
            replace_mode="never",
            cleanup=False,
            retention_keep_last_n=2,
            retention_prefix="Daily Goose ",
        ),
    )

    assert result is not False
    # This fake client's list_items() doesn't grow from put_pdf/upload_pdf calls (unlike the real
    # API), so the retention scan only ever sees the three pre-seeded "Daily Goose" editions
    # (-05, -04, -03), not the one just uploaded - keep_last_n=2 keeps the newest two of those
    # (-05, -04) and deletes -03. The unrelated "Weekly Roundup" document is never touched,
    # confirming the prefix match is doing its job.
    delete_calls = [call for call in client.calls if call[0] == "delete"]
    deleted_ids = {call[1] for call in delete_calls}
    assert deleted_ids == {"doc-2026-08-03"}

    # The retention scan must force a fresh list_items() call (refresh=True) rather than trust
    # whatever was already cached from the folder-resolution scan earlier in upload() - Client
    # only refreshes that cache on put_pdf()/put_epub(), not on the plain upload_pdf()/
    # upload_epub() root-level path, so an unqualified call here could read stale data depending
    # on which path the upload actually took.
    assert ("list_items", True) in client.calls


def test_upload_without_retention_keep_last_n_never_deletes(monkeypatch, tmp_path):
    client = _Client()
    client._items = [
        _IndexedItem("doc-old", "Daily Goose 2026-08-01", "", "DocumentType"),
    ]
    monkeypatch.setattr("goosepaper.upload.auth_client", lambda **kwargs: client)

    filepath = tmp_path / "Daily Goose 2026-08-06.pdf"
    filepath.write_bytes(b"%PDF-test")

    result = upload(filepath, DeliverySettings(replace_mode="never", cleanup=False))

    assert result is not False
    assert not any(call[0] == "delete" for call in client.calls)
