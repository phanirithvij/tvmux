"""Shared test fixtures."""
import pytest


@pytest.fixture
def reset_managed_processes():
    """Reset the global managed processes state before each test."""
    import tvmux.proc.bg as bg_module

    original = bg_module._managed_processes.copy()
    bg_module._managed_processes.clear()

    yield

    bg_module._managed_processes.clear()
    bg_module._managed_processes.update(original)
