from rmapy.api import Client
from rmapy.exceptions import AuthError

CODE_URL = "https://my.remarkable.com/connect/remarkable"

def auth_client():
    client = Client()

    try:
        client.renew_token()
    except AuthError:
        print(
            "Looks like this is the first time you've uploaded. You need to "
            f"register the device. Input a code from {CODE_URL}"
        )
        code = input()
        print("registering")
        client.register_device(code)
        if not client.renew_token():
            print("Honk! Registration renewal failed.")
            return False
        else:
            print("registration successful")

    return client
