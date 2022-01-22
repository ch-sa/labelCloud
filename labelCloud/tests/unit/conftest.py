import logging
import os
from pathlib import Path

import pytest


def pytest_configure(config):
    os.chdir("../labelCloud")
    logging.info(f"Set working directory to {os.getcwd()}.")


@pytest.fixture
def tmppath(tmpdir):
    return Path(tmpdir)
