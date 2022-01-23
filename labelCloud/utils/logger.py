import logging
import shutil
from enum import Enum
from typing import List

# ---------------------------------- CONFIG ---------------------------------- #

# Create handlers
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler(".labelCloud.log", mode="a")
c_handler.setLevel(logging.INFO)  # TODO: Automatic coloring
f_handler.setLevel(logging.DEBUG)  # TODO: Filter colors

# Create formatters and add it to handlers
f_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)-8s: %(message)s"))


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[c_handler, f_handler],
)

# ---------------------------------- HELPERS --------------------------------- #

TERM_SIZE = shutil.get_terminal_size(fallback=(120, 50))


def start_section(text: str):
    left_pad = (TERM_SIZE.columns - len(text)) // 2 - 1
    right_pad = TERM_SIZE.columns - len(text) - left_pad - 2
    logging.info(f"{'=' * left_pad} {text} {'=' * right_pad}")
    pass


def end_section():
    logging.info("=" * TERM_SIZE.columns)
    pass


rows = []


def print_column(column_values: List[str], last: bool = False):
    global rows
    rows.append(column_values)

    if last:
        col_width = max(len(str(word)) for row in rows for word in row) + 2  # padding
        for row in rows:
            logging.info("".join(str(word).ljust(col_width) for word in row))
        rows = []


class Format(Enum):
    RESET = "\033[0;0m"
    RED = "\033[1;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[33m"
    BLUE = "\033[1;34m"
    CYAN = "\033[1;36m"
    BOLD = "\033[;1m"
    REVERSE = "\033[;7m"
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    UNDERLINE = "\033[4m"


def format(text: str, color: Format):
    return f"{color.value}{text}{Format.ENDC.value}"


red = lambda text: format(text, Format.RED)
green = lambda text: format(text, Format.OKGREEN)
yellow = lambda text: format(text, Format.YELLOW)
bold = lambda text: format(text, Format.BOLD)
