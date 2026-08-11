from remarkapy import Client, resolve_config_path
from remarkapy.exceptions import RemarkableAPIError


def auth_client(interactive: bool = True):
    """`interactive` is forwarded to remarkapy's own `Client`, which defaults to `True` there
    too - fine for a real terminal, where a missing device token falls into an `input()` pairing
    wizard. In any unattended context (a cron job, a container with no stdin) that wizard's
    `input()` call raises an uncaught `EOFError` instead of the clean, caught
    `RemarkableAPIError` every other failure here already produces - pass `interactive=False` to
    get that same clean handling (a caught `ConfigNotFoundError`, printed and returned as
    `False`) instead of a crash.
    """
    try:
        client = Client(refresh_on_init=False, interactive=interactive)
        client.refresh_user_token()
        return client
    except RemarkableAPIError as err:
        print(f"Honk! Authentication failed: {err}")
        print(f"remarkapy is using {resolve_config_path()} as its config path.")
        return False
