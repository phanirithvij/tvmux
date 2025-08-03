"""Tests for background process management."""
import os
import signal
import subprocess
import time
from unittest.mock import Mock, patch, MagicMock
import pytest

import tvmux.proc.bg as bg_module


def test_get_children_no_proc(reset_managed_processes):
    """Test _get_children when /proc doesn't exist."""
    with patch('os.listdir', side_effect=OSError("No such directory")):
        children = bg_module._get_children(1234)
        assert children == set()


def test_get_children_with_proc(reset_managed_processes):
    """Test _get_children with mocked /proc."""
    # Mock /proc listing
    with patch('os.listdir', return_value=['1234', '5678', 'not-a-pid']):
        # Mock reading stat files
        def mock_open(path, mode='r'):
            if path == '/proc/1234/stat':
                # PID 1234 has parent PID 1000
                mock_file = MagicMock()
                mock_file.read.return_value = "1234 (process) S 1000 other fields"
                mock_file.__enter__.return_value = mock_file
                return mock_file
            elif path == '/proc/5678/stat':
                # PID 5678 has parent PID 1234 (our target)
                mock_file = MagicMock()
                mock_file.read.return_value = "5678 (child) S 1234 other fields"
                mock_file.__enter__.return_value = mock_file
                return mock_file
            else:
                raise OSError("No such file")

        with patch('builtins.open', mock_open):
            children = bg_module._get_children(1234)
            assert children == {5678}


def test_get_descendants(reset_managed_processes):
    """Test _get_descendants with mocked process tree."""
    # Mock a process tree: 1000 -> 1001 -> 1002
    def mock_get_children(pid):
        if pid == 1000:
            return {1001}
        elif pid == 1001:
            return {1002}
        else:
            return set()

    with patch.object(bg_module, '_get_children', side_effect=mock_get_children):
        descendants = bg_module._get_descendants(1000)
        assert descendants == {1000, 1001, 1002}


def test_terminate_tree_already_dead(reset_managed_processes):
    """Test terminating a process that's already dead."""
    with patch('os.kill', side_effect=ProcessLookupError):
        result = bg_module._terminate_tree(1234)
        assert result is True


def test_terminate_tree_no_permission(reset_managed_processes):
    """Test terminating a process we don't have permission for."""
    with patch('os.kill', side_effect=PermissionError):
        result = bg_module._terminate_tree(1234)
        assert result is False


def test_terminate_tree_graceful_shutdown(reset_managed_processes):
    """Test graceful shutdown with SIGTERM."""
    # Mock process tree
    with patch.object(bg_module, '_get_descendants', return_value={1234, 5678}):
        kill_calls = []

        def mock_kill(pid, sig):
            kill_calls.append((pid, sig))
            if sig == 0 and len([c for c in kill_calls if c[0] == pid and c[1] != 0]) > 0:
                # Process is dead after we sent a signal
                raise ProcessLookupError

        with patch('os.kill', side_effect=mock_kill):
            with patch('time.sleep'):  # Don't actually sleep in tests
                result = bg_module._terminate_tree(1234)
                assert result is True
                # Should have sent SIGTERM to both processes
                assert (1234, signal.SIGTERM) in kill_calls
                assert (5678, signal.SIGTERM) in kill_calls




def test_spawn_process(reset_managed_processes):
    """Test spawning a background process."""
    mock_proc = Mock(spec=subprocess.Popen)
    mock_proc.pid = 1234

    with patch('subprocess.Popen', return_value=mock_proc) as mock_popen:
        proc = bg_module.spawn(['echo', 'test'])

        assert proc == mock_proc
        assert 1234 in bg_module._managed_processes

        # Check default kwargs
        mock_popen.assert_called_once_with(
            ['echo', 'test'],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


def test_spawn_with_custom_kwargs(reset_managed_processes):
    """Test spawning with custom subprocess arguments."""
    mock_proc = Mock(spec=subprocess.Popen)
    mock_proc.pid = 1234

    with patch('subprocess.Popen', return_value=mock_proc) as mock_popen:
        proc = bg_module.spawn(['echo', 'test'], stdout=subprocess.PIPE)

        mock_popen.assert_called_once_with(
            ['echo', 'test'],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )


def test_terminate_tracked_process(reset_managed_processes):
    """Test terminating a tracked process."""
    # Add a fake process to tracking
    bg_module._managed_processes.add(1234)

    with patch.object(bg_module, '_terminate_tree', return_value=True) as mock_term:
        result = bg_module.terminate(1234)

        assert result is True
        assert 1234 not in bg_module._managed_processes
        mock_term.assert_called_once_with(1234, timeout=1.0)


def test_terminate_untracked_process(reset_managed_processes):
    """Test terminating a process that's not tracked."""
    result = bg_module.terminate(9999)
    assert result is False


def test_reap_dead_processes(reset_managed_processes):
    """Test reaping dead processes from tracking."""
    # Add some processes
    bg_module._managed_processes.update({1234, 5678, 9999})

    def mock_kill(pid, sig):
        if pid == 5678:  # This one is dead
            raise ProcessLookupError
        # Others are alive

    with patch('os.kill', side_effect=mock_kill):
        bg_module.reap()

        assert 1234 in bg_module._managed_processes
        assert 5678 not in bg_module._managed_processes
        assert 9999 in bg_module._managed_processes


def test_cleanup_on_exit(reset_managed_processes):
    """Test the cleanup function."""
    # Add some processes
    bg_module._managed_processes.update({1234, 5678})

    with patch.object(bg_module, '_terminate_tree') as mock_term:
        bg_module._cleanup_on_exit()

        # Should have tried to terminate both
        assert mock_term.call_count == 2
        mock_term.assert_any_call(1234, timeout=1.0)
        mock_term.assert_any_call(5678, timeout=1.0)


def test_signal_handler(reset_managed_processes):
    """Test signal handler calls cleanup."""
    with patch.object(bg_module, '_cleanup_on_exit') as mock_cleanup:
        bg_module._signal_handler(signal.SIGTERM, None)
        mock_cleanup.assert_called_once()
