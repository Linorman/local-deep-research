import pytest


@pytest.fixture(autouse=True)
def reset_all_singletons():
    yield
