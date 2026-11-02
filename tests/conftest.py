import pytest

import app.main as main


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Each test starts with empty per-visitor counters."""
    for limit in main.LIMITS.values():
        limit.reset()
    yield
