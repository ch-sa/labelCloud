import os
import sys


def pytest_configure(config):
    os.chdir("../labelCloud")
    print(f"Set working directory to {os.getcwd()}.")

    sys.path.insert(0, "labelCloud")
    print("Added labelCloud to Python path.")

    # preventing circular import
    import app  # noqa: E401
