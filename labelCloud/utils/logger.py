import logging
import re
import shutil
from enum import Enum
from functools import lru_cache
from typing import List

# --------------------------------- FORMATTING -------------------------------- #


class Format(Enum):
    RESET = "\033[0;0m"
    RED = "\033[1;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\33[93m"  # "\033[33m"
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

    GREY = "\33[90m"


def format(text: str, color: Format) -> str:
    return f"{color.value}{text}{Format.ENDC.value}"


red = lambda text: format(text, Format.RED)
green = lambda text: format(text, Format.OKGREEN)
yellow = lambda text: format(text, Format.YELLOW)
blue = lambda text: format(text, Format.BLUE)
bold = lambda text: format(text, Format.BOLD)


class ColorFormatter(logging.Formatter):
    MSG_FORMAT = "%(message)s"

    FORMATS = {
        logging.DEBUG: Format.GREY.value + MSG_FORMAT + Format.ENDC.value,
        logging.INFO: MSG_FORMAT,
        logging.WARNING: Format.YELLOW.value + MSG_FORMAT + Format.ENDC.value,
        logging.ERROR: Format.RED.value + MSG_FORMAT + Format.ENDC.value,
        logging.CRITICAL: Format.RED.value
        + Format.BOLD.value
        + MSG_FORMAT
        + Format.ENDC.value,
    }

    def format(self, record) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class UncolorFormatter(logging.Formatter):
    MSG_FORMAT = "%(asctime)s - %(levelname)-8s: %(message)s"
    PATTERN = re.compile("|".join(re.escape(c.value) for c in Format))

    def format(self, record) -> str:
        record.msg = self.PATTERN.sub("", record.msg)
        formatter = logging.Formatter(self.MSG_FORMAT)
        return formatter.format(record)


# ---------------------------------- CONFIG ---------------------------------- #

# Create handlers
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler(".labelCloud.log", mode="w")
c_handler.setLevel(logging.INFO)  # TODO: Automatic coloring
f_handler.setLevel(logging.DEBUG)  # TODO: Filter colors

# Create formatters and add it to handlers
c_handler.setFormatter(ColorFormatter())
f_handler.setFormatter(UncolorFormatter())


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[c_handler, f_handler],
)


# ---------------------------------- HELPERS --------------------------------- #

TERM_SIZE = shutil.get_terminal_size(fallback=(120, 50))


def start_section(text: str) -> None:
    left_pad = (TERM_SIZE.columns - len(text)) // 2 - 1
    right_pad = TERM_SIZE.columns - len(text) - left_pad - 2
    logging.info(f"{'=' * left_pad} {text} {'=' * right_pad}")
    pass


def end_section() -> None:
    logging.info("=" * TERM_SIZE.columns)
    pass


ROWS: List[List[str]] = []


def print_column(column_values: List[str], last: bool = False) -> None:
    global ROWS
    ROWS.append(column_values)

    if last:
        col_width = max(len(str(word)) for row in ROWS for word in row) + 2  # padding
        for row in ROWS:
            logging.info("".join(str(word).ljust(col_width) for word in row))
        ROWS = []


@lru_cache(maxsize=None)
def warn_once(*args, **kwargs):
    logging.warning(*args, **kwargs)
