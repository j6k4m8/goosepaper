from remarkapy import Client, resolve_config_path
from remarkapy.exceptions import RemarkableAPIError


def auth_client():
    try:
        client = Client(refresh_on_init=False)
        client.refresh_user_token()
        return client
    except RemarkableAPIError as err:
        print(f"Honk! Authentication failed: {err}")
        print(f"remarkapy is using {resolve_config_path()} as its config path.")
        return False
