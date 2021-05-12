from rmapy.api import Client
from rmapy.exceptions import AuthError

def auth_client():
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
            print("Honk! Registration failed D:")
            return False
        else:
            print("registration successful")

    return client
