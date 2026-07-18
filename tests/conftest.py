import pytest
from pathlib import Path

from settings import load_config

_TEST_CONFIG_PATH = Path(__file__).parent.parent / "config" / "config-example.yaml"


@pytest.fixture
def app_config():
    return load_config(_TEST_CONFIG_PATH)
