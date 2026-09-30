import pytest


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Every test gets its own temp SQLite file so tests never touch the real dev database."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
