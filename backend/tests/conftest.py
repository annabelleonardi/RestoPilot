"""Shared pytest fixtures: deterministic fresh-seeded demo DB per test."""

import os

import pytest

from app.db.session import engine


@pytest.fixture(scope="function", autouse=True)
def fresh_db():
    """Start every test from a freshly seeded restopilot.db so both absolute
    seed assertions (dashboard aggregates, low-stock counts) and delta-based
    assertions stay deterministic no matter which files ran before."""
    # Drop pooled connections first: a deleted SQLite file leaves stale
    # descriptors that surface as "attempt to write a readonly database".
    engine.dispose()
    if os.path.exists("restopilot.db"):
        os.remove("restopilot.db")
    yield
