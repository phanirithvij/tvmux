"""Tests for configuration system."""
import os
import tempfile
from pathlib import Path

import pytest

from tvmux.config import (
    Config, load_config, set_config, get_config,
    generate_env_var_name, get_all_env_mappings, load_all_env_overrides,
    _convert_env_value, dump_config_toml, dump_config_env
)


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

    # Set environment variables (using new programmatic names)
    old_env = {}
    env_vars = {
        "TVMUX_OUTPUT_DIRECTORY": "/from/env",
        "TVMUX_SERVER_PORT": "9999",
        "TVMUX_SERVER_AUTO_START": "false"
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
        ("on", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("off", False)
    ]

    old_env = os.environ.get("TVMUX_SERVER_AUTO_START")

    try:
        for env_value, expected in test_cases:
            os.environ["TVMUX_SERVER_AUTO_START"] = env_value
            config = load_config()
            assert config.server.auto_start is expected, f"Failed for {env_value}"
    finally:
        if old_env is None:
            os.environ.pop("TVMUX_SERVER_AUTO_START", None)
        else:
            os.environ["TVMUX_SERVER_AUTO_START"] = old_env


def test_path_expansion():
    """Test that ~ expansion works in directory paths."""
    config = Config(output={"directory": "~/test/path"})

    # The config itself stores the raw value
    assert config.output.directory == "~/test/path"

    # Path expansion happens when the path is used
    expanded = Path(config.output.directory).expanduser()
    assert str(expanded).startswith(str(Path.home()))
    assert str(expanded).endswith("test/path")


def test_generate_env_var_name():
    """Test environment variable name generation."""
    assert generate_env_var_name("output", "directory") == "TVMUX_OUTPUT_DIRECTORY"
    assert generate_env_var_name("server", "port") == "TVMUX_SERVER_PORT"
    assert generate_env_var_name("recording", "repair_on_stop") == "TVMUX_RECORDING_REPAIR_ON_STOP"
    assert generate_env_var_name("annotations", "include_cursor_state") == "TVMUX_ANNOTATIONS_INCLUDE_CURSOR_STATE"


def test_get_all_env_mappings():
    """Test that env var mappings follow expected conventions and core fields exist."""
    mappings = get_all_env_mappings()

    # Should have mappings (non-empty)
    assert mappings, "Should have at least some environment variable mappings"

    # All env vars should follow TVMUX_* convention
    for env_var in mappings.keys():
        assert env_var.startswith("TVMUX_"), f"Environment variable {env_var} should start with TVMUX_"

    # All mappings should be (section, field) tuples
    for env_var, mapping in mappings.items():
        assert isinstance(mapping, tuple) and len(mapping) == 2, f"Mapping for {env_var} should be (section, field) tuple"
        section, field = mapping
        assert isinstance(section, str) and isinstance(field, str), f"Section and field for {env_var} should be strings"

    # Core output directory field should always be mappable (this is fundamental to the app)
    assert "TVMUX_OUTPUT_DIRECTORY" in mappings
    assert mappings["TVMUX_OUTPUT_DIRECTORY"] == ("output", "directory")


def test_convert_env_value():
    """Test environment variable value conversion."""
    # Boolean values
    assert _convert_env_value("true") is True
    assert _convert_env_value("True") is True
    assert _convert_env_value("1") is True
    assert _convert_env_value("yes") is True
    assert _convert_env_value("on") is True

    assert _convert_env_value("false") is False
    assert _convert_env_value("False") is False
    assert _convert_env_value("0") is False
    assert _convert_env_value("no") is False
    assert _convert_env_value("off") is False

    # Integer values
    assert _convert_env_value("123") == 123
    assert _convert_env_value("0") == 0  # Note: This tests the int conversion before bool
    assert _convert_env_value("-456") == -456

    # String values
    assert _convert_env_value("hello") == "hello"
    assert _convert_env_value("/some/path") == "/some/path"
    assert _convert_env_value("%Y-%m") == "%Y-%m"


def test_load_all_env_overrides():
    """Test programmatic environment variable loading."""
    # Set up some test environment variables
    test_env_vars = {
        "TVMUX_OUTPUT_DIRECTORY": "/test/env/path",
        "TVMUX_SERVER_PORT": "8888",
        "TVMUX_SERVER_AUTO_START": "false",
        "TVMUX_RECORDING_REPAIR_ON_STOP": "true",
        "TVMUX_ANNOTATIONS_INCLUDE_CURSOR_STATE": "false"
    }

    # Store original values
    original_values = {}
    for env_var in test_env_vars:
        original_values[env_var] = os.environ.get(env_var)

    # Set test values
    for env_var, value in test_env_vars.items():
        os.environ[env_var] = value

    try:
        overrides = load_all_env_overrides()

        # Check structure and values
        assert "output" in overrides
        assert "server" in overrides
        assert "recording" in overrides
        assert "annotations" in overrides

        assert overrides["output"]["directory"] == "/test/env/path"
        assert overrides["server"]["port"] == 8888
        assert overrides["server"]["auto_start"] is False
        assert overrides["recording"]["repair_on_stop"] is True
        assert overrides["annotations"]["include_cursor_state"] is False

    finally:
        # Restore original environment
        for env_var, original_value in original_values.items():
            if original_value is None:
                os.environ.pop(env_var, None)
            else:
                os.environ[env_var] = original_value


def test_dump_config_toml():
    """Test TOML configuration output."""
    config = Config(
        output={"directory": "/test/path", "date_format": "%Y-%m-%d"},
        server={"port": 9999, "auto_start": False}
    )

    toml_output = dump_config_toml(config)

    # Should be valid TOML
    assert "[output]" in toml_output
    assert "[server]" in toml_output
    assert 'directory = "/test/path"' in toml_output
    assert 'date_format = "%Y-%m-%d"' in toml_output
    assert "port = 9999" in toml_output
    assert "auto_start = false" in toml_output


def test_dump_config_env():
    """Test environment variable configuration output."""
    config = Config(
        output={"directory": "/test/path", "date_format": "%Y-%m-%d"},
        server={"port": 9999, "auto_start": False},
        recording={"repair_on_stop": True}
    )

    env_output = dump_config_env(config)
    lines = env_output.split("\n")

    # Should have all expected variables
    expected_lines = {
        "TVMUX_OUTPUT_DIRECTORY=/test/path",
        "TVMUX_OUTPUT_DATE_FORMAT=%Y-%m-%d",
        "TVMUX_SERVER_PORT=9999",
        "TVMUX_SERVER_AUTO_START=false",
        "TVMUX_SERVER_AUTO_SHUTDOWN=true",
        "TVMUX_RECORDING_REPAIR_ON_STOP=true",
        "TVMUX_RECORDING_FOLLOW_ACTIVE_PANE=true",
        "TVMUX_ANNOTATIONS_INCLUDE_CURSOR_STATE=true"
    }

    for expected_line in expected_lines:
        assert expected_line in lines


def test_comprehensive_env_var_coverage():
    """Test that new programmatic approach covers all config fields."""
    # Create config with all non-default values
    config = Config(
        output={"directory": "/custom", "date_format": "%Y"},
        server={"port": 8888, "auto_start": False, "auto_shutdown": False},
        recording={"repair_on_stop": False, "follow_active_pane": False},
        annotations={"include_cursor_state": False}
    )

    # Set all corresponding environment variables
    env_lines = dump_config_env(config).split("\n")

    # Clear environment first
    for line in env_lines:
        if "=" in line:
            env_var = line.split("=")[0]
            os.environ.pop(env_var, None)

    # Set all env vars from the config
    for line in env_lines:
        if "=" in line:
            env_var, value = line.split("=", 1)
            os.environ[env_var] = value

    try:
        # Load config using environment variables
        loaded_config = load_config()

        # Should match the original config
        assert loaded_config.output.directory == "/custom"
        assert loaded_config.output.date_format == "%Y"
        assert loaded_config.server.port == 8888
        assert loaded_config.server.auto_start is False
        assert loaded_config.server.auto_shutdown is False
        assert loaded_config.recording.repair_on_stop is False
        assert loaded_config.recording.follow_active_pane is False
        assert loaded_config.annotations.include_cursor_state is False

    finally:
        # Clean up environment
        for line in env_lines:
            if "=" in line:
                env_var = line.split("=")[0]
                os.environ.pop(env_var, None)
