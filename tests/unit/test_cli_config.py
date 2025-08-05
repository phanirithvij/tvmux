"""Tests for config CLI commands."""
import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from tvmux.cli.config import config
from tvmux.config import Config, set_config


@pytest.fixture
def runner():
    """Provide a Click test runner."""
    return CliRunner()


@pytest.fixture
def reset_global_config():
    """Reset global config after each test."""
    original_config = None
    try:
        from tvmux.config import _config
        original_config = _config
        yield
    finally:
        set_config(original_config)


def test_config_show_toml(runner, reset_global_config):
    """Test tvmux config show command with TOML output."""
    # Set a custom config
    custom_config = Config(
        output={"directory": "/test/recordings", "date_format": "%Y-%W"},
        server={"port": 8888, "auto_start": False}
    )
    set_config(custom_config)

    result = runner.invoke(config, ['show'])

    assert result.exit_code == 0
    output = result.output

    # Should be TOML format
    assert "[output]" in output
    assert "[server]" in output
    assert 'directory = "/test/recordings"' in output
    assert 'date_format = "%Y-%W"' in output
    assert "port = 8888" in output
    assert "auto_start = false" in output


def test_config_show_env(runner, reset_global_config):
    """Test tvmux config show --format=env command."""
    # Set a custom config
    custom_config = Config(
        output={"directory": "/env/test", "date_format": "%Y"},
        server={"port": 9999, "auto_start": True, "auto_shutdown": False},
        recording={"repair_on_stop": False}
    )
    set_config(custom_config)

    result = runner.invoke(config, ['show', '--format', 'env'])

    assert result.exit_code == 0
    output_lines = result.output.strip().split('\n')

    # Should be environment variable format
    expected_vars = {
        "TVMUX_OUTPUT_DIRECTORY=/env/test",
        "TVMUX_OUTPUT_DATE_FORMAT=%Y",
        "TVMUX_SERVER_PORT=9999",
        "TVMUX_SERVER_AUTO_START=true",
        "TVMUX_SERVER_AUTO_SHUTDOWN=false",
        "TVMUX_RECORDING_REPAIR_ON_STOP=false",
        "TVMUX_RECORDING_FOLLOW_ACTIVE_PANE=true",
        "TVMUX_ANNOTATIONS_INCLUDE_CURSOR_STATE=true"
    }

    for expected_var in expected_vars:
        assert expected_var in output_lines


def test_config_defaults_toml(runner):
    """Test tvmux config defaults command with TOML output."""
    result = runner.invoke(config, ['defaults'])

    assert result.exit_code == 0
    output = result.output

    # Should be TOML format with default values
    assert "[output]" in output
    assert "[server]" in output
    assert "[recording]" in output
    assert "[annotations]" in output
    assert 'directory = "~/Videos/tmux"' in output
    assert 'date_format = "%Y-%m"' in output
    assert "port = 21590" in output
    assert "auto_start = true" in output
    assert "auto_shutdown = true" in output
    assert "repair_on_stop = true" in output
    assert "follow_active_pane = true" in output
    assert "include_cursor_state = true" in output


def test_config_defaults_env(runner):
    """Test tvmux config defaults --format=env command."""
    result = runner.invoke(config, ['defaults', '--format', 'env'])

    assert result.exit_code == 0
    output_lines = result.output.strip().split('\n')

    # Should be environment variable format with default values
    expected_defaults = {
        "TVMUX_OUTPUT_DIRECTORY=~/Videos/tmux",
        "TVMUX_OUTPUT_DATE_FORMAT=%Y-%m",
        "TVMUX_SERVER_PORT=21590",
        "TVMUX_SERVER_AUTO_START=true",
        "TVMUX_SERVER_AUTO_SHUTDOWN=true",
        "TVMUX_RECORDING_REPAIR_ON_STOP=true",
        "TVMUX_RECORDING_FOLLOW_ACTIVE_PANE=true",
        "TVMUX_ANNOTATIONS_INCLUDE_CURSOR_STATE=true"
    }

    for expected_default in expected_defaults:
        assert expected_default in output_lines


def test_config_show_with_file_and_env(runner, reset_global_config):
    """Test config show reflects file + environment overrides."""
    # Create a temporary config file
    toml_content = """
[output]
directory = "/from/file"
date_format = "%Y-%m-%d"

[server]
port = 7777
auto_start = true
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(toml_content)
        config_path = f.name

    # Set environment override
    old_env = os.environ.get("TVMUX_SERVER_PORT")
    os.environ["TVMUX_SERVER_PORT"] = "8888"

    try:
        # Load config with file and env override
        from tvmux.config import load_config
        test_config = load_config(config_path)
        set_config(test_config)

        result = runner.invoke(config, ['show', '--format', 'env'])

        assert result.exit_code == 0
        output_lines = result.output.strip().split('\n')

        # Environment should override file
        assert "TVMUX_OUTPUT_DIRECTORY=/from/file" in output_lines  # from file
        assert "TVMUX_SERVER_PORT=8888" in output_lines  # from env override

    finally:
        # Clean up
        if old_env is None:
            os.environ.pop("TVMUX_SERVER_PORT", None)
        else:
            os.environ["TVMUX_SERVER_PORT"] = old_env
        os.unlink(config_path)


def test_config_invalid_format(runner):
    """Test config commands with invalid format."""
    result = runner.invoke(config, ['show', '--format', 'invalid'])

    assert result.exit_code != 0
    assert "Invalid value for '--format'" in result.output


def test_config_help(runner):
    """Test config command help."""
    result = runner.invoke(config, ['--help'])

    assert result.exit_code == 0
    assert "Configuration management commands" in result.output
    assert "show" in result.output
    assert "defaults" in result.output


def test_config_show_help(runner):
    """Test config show subcommand help."""
    result = runner.invoke(config, ['show', '--help'])

    assert result.exit_code == 0
    assert "Show current effective configuration" in result.output
    assert "--format" in result.output
    assert "toml" in result.output
    assert "env" in result.output


def test_config_defaults_help(runner):
    """Test config defaults subcommand help."""
    result = runner.invoke(config, ['defaults', '--help'])

    assert result.exit_code == 0
    assert "Show default configuration values" in result.output
    assert "--format" in result.output
