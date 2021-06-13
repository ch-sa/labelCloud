import os
import sys


def pytest_configure(config):
    os.chdir("../labelCloud")
    print(f"Set working directory to {os.getcwd()}.")

    sys.path.insert(0, "labelCloud")
    print(f"Added labelCloud to Python path.")

    import app  # preventing circular import