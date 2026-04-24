from remarkapy import RemarkapyConfig, get_config_or_raise, resolve_config_path
from remarkapy.configfile import DEFAULT_CONFIG_PATH, write_config


def test_remarkapy_default_config_path_is_rmapi():
    assert DEFAULT_CONFIG_PATH.name == ".rmapi"


def test_remarkapy_reads_rmapi_compatible_config(tmp_path):
    config_path = tmp_path / ".rmapi"
    write_config(
        config_path,
        RemarkapyConfig(
            devicetoken="device-token",
            usertoken="user-token",
        ),
    )

    assert resolve_config_path(config_path) == config_path.resolve()
    config = get_config_or_raise(config_path)
    assert config.devicetoken == "device-token"
    assert config.usertoken == "user-token"
