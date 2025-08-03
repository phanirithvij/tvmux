"""Tests for file_has_readers function."""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import psutil
from tvmux.utils import file_has_readers


def test_file_has_readers_no_processes():
    """Test when no processes are running."""
    with patch('psutil.process_iter', return_value=[]):
        assert file_has_readers("/tmp/test.fifo") is False


def test_file_has_readers_no_tail_processes():
    """Test when processes exist but none are tail."""
    mock_proc = Mock()
    mock_proc.info = {'pid': 1234, 'cmdline': ['vim', '/tmp/file.txt']}

    with patch('psutil.process_iter', return_value=[mock_proc]):
        assert file_has_readers("/tmp/test.fifo") is False


def test_file_has_readers_tail_different_file():
    """Test when tail process exists but for different file."""
    mock_proc = Mock()
    mock_proc.info = {'pid': 1234, 'cmdline': ['tail', '-f', '/tmp/other.fifo']}

    with patch('psutil.process_iter', return_value=[mock_proc]):
        assert file_has_readers("/tmp/test.fifo") is False


def test_file_has_readers_tail_matching_file():
    """Test when tail process exists for our file."""
    mock_proc = Mock()
    mock_proc.info = {'pid': 1234, 'cmdline': ['tail', '-f', '/tmp/test.fifo']}

    with patch('psutil.process_iter', return_value=[mock_proc]):
        assert file_has_readers("/tmp/test.fifo") is True


def test_file_has_readers_tail_with_full_path():
    """Test when tail process has full path but we check basename."""
    mock_proc = Mock()
    mock_proc.info = {'pid': 1234, 'cmdline': ['tail', '-f', '/full/path/to/test.fifo']}

    # Should match based on filename only
    with patch('psutil.process_iter', return_value=[mock_proc]):
        assert file_has_readers("/different/path/test.fifo") is True


def test_file_has_readers_multiple_processes():
    """Test with multiple processes, some tail, some not."""
    procs = [
        Mock(info={'pid': 1, 'cmdline': ['vim', 'file.txt']}),
        Mock(info={'pid': 2, 'cmdline': ['tail', '-f', '/tmp/other.fifo']}),
        Mock(info={'pid': 3, 'cmdline': ['tail', '-f', '/tmp/test.fifo']}),
        Mock(info={'pid': 4, 'cmdline': ['grep', 'pattern', 'file.txt']}),
    ]

    with patch('psutil.process_iter', return_value=procs):
        assert file_has_readers("/tmp/test.fifo") is True


def test_file_has_readers_process_exceptions():
    """Test handling of psutil exceptions."""
    good_proc = Mock()
    good_proc.info = {'pid': 1234, 'cmdline': ['tail', '-f', '/tmp/test.fifo']}

    bad_proc = Mock()
    bad_proc.info = Mock(side_effect=psutil.NoSuchProcess(123))

    with patch('psutil.process_iter', return_value=[bad_proc, good_proc]):
        with patch('psutil.NoSuchProcess', Exception):  # Mock the exception
            assert file_has_readers("/tmp/test.fifo") is True


def test_file_has_readers_empty_cmdline():
    """Test when process has empty cmdline."""
    mock_proc = Mock()
    mock_proc.info = {'pid': 1234, 'cmdline': None}

    with patch('psutil.process_iter', return_value=[mock_proc]):
        assert file_has_readers("/tmp/test.fifo") is False


def test_file_has_readers_cmdline_with_tail_substring():
    """Test when cmdline contains 'tail' as a separate argument."""
    mock_proc = Mock()
    mock_proc.info = {'pid': 1234, 'cmdline': ['some-program', 'tail', '/tmp/test.fifo']}

    with patch('psutil.process_iter', return_value=[mock_proc]):
        # Should match because 'tail' is in cmdline list
        assert file_has_readers("/tmp/test.fifo") is True


def test_file_has_readers_with_real_fifo():
    """Test with actual temporary FIFO file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fifo_path = Path(tmpdir) / "test.fifo"

        # Mock a tail process for this specific FIFO
        mock_proc = Mock()
        mock_proc.info = {'pid': 1234, 'cmdline': ['tail', '-f', str(fifo_path)]}

        with patch('psutil.process_iter', return_value=[mock_proc]):
            assert file_has_readers(str(fifo_path)) is True


def test_file_has_readers_case_sensitivity():
    """Test case sensitivity in filename matching."""
    mock_proc = Mock()
    mock_proc.info = {'pid': 1234, 'cmdline': ['tail', '-f', '/tmp/TEST.fifo']}

    with patch('psutil.process_iter', return_value=[mock_proc]):
        # Should not match due to case difference
        assert file_has_readers("/tmp/test.fifo") is False
