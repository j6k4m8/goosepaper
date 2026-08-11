from remarkapy.exceptions import ConfigNotFoundError

from . import auth


class _FakeClient:
    def __init__(self, refresh_on_init=False, interactive=True, has_token=True):
        self.refresh_on_init = refresh_on_init
        self.interactive = interactive
        self.has_token = has_token

    def refresh_user_token(self):
        if not self.has_token and not self.interactive:
            # Mirrors remarkapy's own Client.refresh_user_token(): with no device token and
            # interactive pairing disabled, this is what actually gets raised - a clean,
            # RemarkableAPIError-derived exception auth_client()'s except block already handles,
            # rather than falling into an input()-based pairing wizard that would raise an
            # uncaught EOFError in a context with no stdin (a cron job, a container).
            raise ConfigNotFoundError(
                "No device token is configured and interactive pairing is disabled."
            )
        return "token"


def test_auth_client_defaults_to_interactive_for_backward_compatibility(monkeypatch):
    seen = {}

    def fake_client(**kwargs):
        seen.update(kwargs)
        return _FakeClient(**kwargs)

    monkeypatch.setattr(auth, "Client", fake_client)

    result = auth.auth_client()

    assert seen["interactive"] is True
    assert result is not False


def test_auth_client_passes_interactive_false_through_to_client(monkeypatch):
    seen = {}

    def fake_client(**kwargs):
        seen.update(kwargs)
        return _FakeClient(**kwargs)

    monkeypatch.setattr(auth, "Client", fake_client)

    result = auth.auth_client(interactive=False)

    assert seen["interactive"] is False
    assert result is not False


def test_auth_client_fails_cleanly_instead_of_crashing_when_noninteractive_and_unpaired(
    monkeypatch,
):
    monkeypatch.setattr(
        auth, "Client", lambda **kwargs: _FakeClient(has_token=False, **kwargs)
    )

    result = auth.auth_client(interactive=False)

    assert result is False
