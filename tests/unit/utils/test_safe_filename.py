"""Tests for safe_filename function."""
import pytest
from tvmux.utils import safe_filename


def test_safe_filename_basic():
    """Test basic filename sanitization."""
    assert safe_filename("hello") == "hello"
    assert safe_filename("hello world") == "hello world"


def test_safe_filename_removes_path_separators():
    """Test that path separators are replaced."""
    assert safe_filename("hello/world") == "hello_world"
    assert safe_filename("hello\\world") == "hello_world"


def test_safe_filename_removes_newlines():
    """Test that newlines are replaced with underscores."""
    assert safe_filename("hello\nworld") == "hello_world"
    assert safe_filename("hello\r\nworld") == "hello__world"


def test_safe_filename_removes_control_characters():
    """Test that control characters are removed."""
    assert safe_filename("hello\tworld") == "hello_world"
    assert safe_filename("hello\x00world") == "hello_world"


def test_safe_filename_removes_windows_reserved():
    """Test that Windows reserved characters are replaced."""
    assert safe_filename("hello<world>") == "hello_world_"
    assert safe_filename('hello:world|test"') == "hello_world_test_"
    assert safe_filename("hello?world*") == "hello_world_"


def test_safe_filename_truncates_long_names():
    """Test that very long filenames are truncated."""
    long_name = "a" * 150
    result = safe_filename(long_name)
    assert len(result) == 100
    assert result == "a" * 100


def test_safe_filename_handles_empty_string():
    """Test that empty strings stay empty."""
    assert safe_filename("") == ""
    assert safe_filename("   ") == "   "


def test_safe_filename_handles_only_bad_chars():
    """Test that strings with only bad characters become underscores."""
    assert safe_filename("/\\<>:|?*") == "________"
    assert safe_filename("\n\r\t\x00") == "____"


def test_safe_filename_real_world_examples():
    """Test with real-world problematic names."""
    # tmux window IDs with newlines (the actual bug)
    assert safe_filename("@0\n@1") == "@0_@1"

    # Session names with various characters
    assert safe_filename("my-project: work/dev") == "my-project_ work_dev"

    # Window names with problematic chars
    assert safe_filename("vim /etc/hosts") == "vim _etc_hosts"
