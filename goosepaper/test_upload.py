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

    def list_items(self):
        self.calls.append("list_items")
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
    monkeypatch.setattr("goosepaper.upload.auth_client", lambda: client)

    filepath = tmp_path / "paper.pdf"
    filepath.write_bytes(b"%PDF-test")

    result = upload(filepath, DeliverySettings(folder=None, replace_mode="never", cleanup=False))

    assert result is not False
    assert ("upload_pdf", "paper", b"%PDF-test") in client.calls
    assert "list_items" not in client.calls


def test_upload_with_folder_scans_minimal_index(monkeypatch, tmp_path):
    client = _Client()
    client._items = [_IndexedItem("folder-1", "News", "", "CollectionType")]
    monkeypatch.setattr("goosepaper.upload.auth_client", lambda: client)

    filepath = tmp_path / "paper.pdf"
    filepath.write_bytes(b"%PDF-test")

    result = upload(filepath, DeliverySettings(folder="News", replace_mode="never", cleanup=False))

    assert result is not False
    assert "list_items" in client.calls
    assert ("put_pdf", "paper", b"%PDF-test", "folder-1", True) in client.calls


def test_upload_with_new_folder_uses_put_folder_and_nested_put_pdf(monkeypatch, tmp_path):
    client = _Client()
    monkeypatch.setattr("goosepaper.upload.auth_client", lambda: client)

    filepath = tmp_path / "paper.pdf"
    filepath.write_bytes(b"%PDF-test")

    result = upload(filepath, DeliverySettings(folder="News", replace_mode="never", cleanup=False))

    assert result is not False
    assert ("put_folder", "News", "", True) in client.calls
    assert ("put_pdf", "paper", b"%PDF-test", "folder-1", True) in client.calls
