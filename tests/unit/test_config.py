"""Tests for configuration system."""
import os
import tempfile
from pathlib import Path

import pytest

from tvmux.config import Config, load_config, set_config, get_config


def test_default_config():
    """Test default configuration values."""
    config = Config()

    assert config.output.directory == "~/Videos/tmux"
    assert config.output.date_format == "%Y-%m"
    assert config.server.port == 21590
    assert config.server.auto_start is True
    assert config.server.auto_shutdown is True
    assert config.recording.repair_on_stop is True
    assert config.recording.follow_active_pane is True
    assert config.annotations.include_cursor_state is True


def test_config_from_dict():
    """Test creating config from dictionary."""
    config_data = {
        "output": {
            "directory": "/custom/path",
            "date_format": "%Y/%m/%d"
        },
        "server": {
            "port": 9999,
            "auto_start": False
        }
    }

    config = Config(**config_data)

    assert config.output.directory == "/custom/path"
    assert config.output.date_format == "%Y/%m/%d"
    assert config.server.port == 9999
    assert config.server.auto_start is False
    # Defaults should still apply
    assert config.server.auto_shutdown is True
    assert config.recording.repair_on_stop is True


def test_load_config_no_file():
    """Test loading config when no file exists."""
    config = load_config("/nonexistent/path")

    # Should return defaults
    assert config.output.directory == "~/Videos/tmux"
    assert config.server.port == 21590


def test_load_config_from_file():
    """Test loading config from TOML file."""
    toml_content = """
[output]
directory = "/test/recordings"
date_format = "%Y-%W"

[server]
port = 8888
auto_start = false

[recording]
repair_on_stop = false
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(toml_content)
        config_path = f.name

    try:
        config = load_config(config_path)

        assert config.output.directory == "/test/recordings"
        assert config.output.date_format == "%Y-%W"
        assert config.server.port == 8888
        assert config.server.auto_start is False
        assert config.recording.repair_on_stop is False
        # Defaults should still apply for unspecified values
        assert config.server.auto_shutdown is True
        assert config.annotations.include_cursor_state is True
    finally:
        os.unlink(config_path)


def test_environment_variable_overrides():
    """Test environment variable overrides."""
    toml_content = """
[output]
directory = "/from/file"

[server]
port = 7777
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(toml_content)
        config_path = f.name

    # Set environment variables
    old_env = {}
    env_vars = {
        "TVMUX_OUTPUT_DIR": "/from/env",
        "TVMUX_SERVER_PORT": "9999",
        "TVMUX_AUTO_START": "false"
    }

    for key, value in env_vars.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        config = load_config(config_path)

        # Environment variables should override file values
        assert config.output.directory == "/from/env"
        assert config.server.port == 9999
        assert config.server.auto_start is False
    finally:
        # Restore environment
        for key, old_value in old_env.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value
        os.unlink(config_path)


def test_environment_config_file():
    """Test TVMUX_CONFIG_FILE environment variable."""
    toml_content = """
[server]
port = 5555
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(toml_content)
        config_path = f.name

    old_env = os.environ.get("TVMUX_CONFIG_FILE")
    os.environ["TVMUX_CONFIG_FILE"] = config_path

    try:
        config = load_config()  # No explicit path
        assert config.server.port == 5555
    finally:
        if old_env is None:
            os.environ.pop("TVMUX_CONFIG_FILE", None)
        else:
            os.environ["TVMUX_CONFIG_FILE"] = old_env
        os.unlink(config_path)


def test_global_config_management():
    """Test global config get/set functions."""
    # Initially None
    from tvmux.config import _config
    original_config = _config

    # Reset to None for testing
    set_config(None)

    try:
        # First call should load defaults
        config1 = get_config()
        assert config1.server.port == 21590

        # Second call should return same instance
        config2 = get_config()
        assert config2 is config1

        # Set custom config
        custom_config = Config(server={"port": 8888})
        set_config(custom_config)

        config3 = get_config()
        assert config3 is custom_config
        assert config3.server.port == 8888
    finally:
        # Restore original
        set_config(original_config)


def test_boolean_env_vars():
    """Test boolean environment variable parsing."""
    test_cases = [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("anything_else", False)
    ]

    old_env = os.environ.get("TVMUX_AUTO_START")

    try:
        for env_value, expected in test_cases:
            os.environ["TVMUX_AUTO_START"] = env_value
            config = load_config()
            assert config.server.auto_start is expected, f"Failed for {env_value}"
    finally:
        if old_env is None:
            os.environ.pop("TVMUX_AUTO_START", None)
        else:
            os.environ["TVMUX_AUTO_START"] = old_env


def test_path_expansion():
    """Test that ~ expansion works in directory paths."""
    config = Config(output={"directory": "~/test/path"})

    # The config itself stores the raw value
    assert config.output.directory == "~/test/path"

    # Path expansion happens when the path is used
    expanded = Path(config.output.directory).expanduser()
    assert str(expanded).startswith(str(Path.home()))
    assert str(expanded).endswith("test/path")
