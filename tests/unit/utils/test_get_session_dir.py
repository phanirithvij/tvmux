"""Tests for get_session_dir function."""
from pathlib import Path
from tvmux.utils import get_session_dir


def test_get_session_dir_basic():
    """Test basic session directory generation."""
    result = get_session_dir("laptop", "main", "/tmp/tmux-1000/default,3028,0")

    assert isinstance(result, Path)
    assert str(result).startswith("/run/tvmux/session_laptop_main_")
    assert len(str(result.name)) <= 50  # Reasonable length


def test_get_session_dir_with_spaces():
    """Test session name with spaces gets cleaned."""
    result = get_session_dir("host", "my project", "/tmp/tmux-1000/default,3028,0")

    assert "my_project" in str(result)
    assert " " not in str(result.name)


def test_get_session_dir_with_special_chars():
    """Test session name with special characters gets cleaned."""
    result = get_session_dir("host", "my/project:work", "/tmp/tmux-1000/default,3028,0")

    assert "my_project_work" in str(result)
    assert "/" not in str(result.name)
    assert ":" not in str(result.name)


def test_get_session_dir_long_name_truncated():
    """Test very long session names get truncated."""
    long_name = "a" * 50
    result = get_session_dir("host", long_name, "/tmp/tmux-1000/default,3028,0")

    # Should be truncated to 20 chars
    name_parts = str(result.name).split("_")
    session_part = name_parts[2]  # session_host_SESSION_hash
    assert len(session_part) == 20


def test_get_session_dir_collision_protection():
    """Test that different sessions get different directories."""
    result1 = get_session_dir("host", "session", "/tmp/tmux-1000/default,3028,0")
    result2 = get_session_dir("host", "session", "/tmp/tmux-1000/default,3029,0")

    # Same session name but different tmux vars should produce different paths
    assert result1 != result2


def test_get_session_dir_same_inputs_same_output():
    """Test that identical inputs produce identical outputs."""
    tmux_var = "/tmp/tmux-1000/default,3028,0"
    result1 = get_session_dir("host", "session", tmux_var)
    result2 = get_session_dir("host", "session", tmux_var)

    assert result1 == result2


def test_get_session_dir_custom_base_dir():
    """Test using custom base directory."""
    result = get_session_dir("host", "session", "/tmp/tmux-1000/default,3028,0", "/custom/path")

    assert str(result).startswith("/custom/path/session_host_session_")


def test_get_session_dir_empty_session_name():
    """Test with empty session name."""
    result = get_session_dir("host", "", "/tmp/tmux-1000/default,3028,0")

    # Should still work, just with empty session part
    assert "session_host__" in str(result)


def test_get_session_dir_hash_consistency():
    """Test that hash part is consistent and reasonable length."""
    result = get_session_dir("laptop", "main", "/tmp/tmux-1000/default,3028,0")

    # Hash should be 6 characters (MD5 truncated)
    hash_part = str(result.name).split("_")[-1]
    assert len(hash_part) == 6
    assert hash_part.isalnum()


def test_get_session_dir_hostname_variations():
    """Test different hostnames produce different results."""
    tmux_var = "/tmp/tmux-1000/default,3028,0"
    result1 = get_session_dir("host1", "session", tmux_var)
    result2 = get_session_dir("host2", "session", tmux_var)

    assert result1 != result2
    assert "host1" in str(result1)
    assert "host2" in str(result2)
