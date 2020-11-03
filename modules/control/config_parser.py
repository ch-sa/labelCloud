"""Load configuration from .ini file."""
import configparser

# Read local file `config.ini`.
from typing import List, Union

config = configparser.ConfigParser()
config.read("config.ini")


# Parses string to list if it contains a ","
def float_parser_decorator(func):
    def wrapper(*args, **kwargs):
        value = func(*args, **kwargs)
        if value in ["True", "False"]:
            return value == "True"
        try:
            return float(value)
        except TypeError:
            return value
        except ValueError:
            return value

    return wrapper


# Parses string to list if it contains a ","
def list_parser_decorator(func):
    def wrapper(*args, **kwargs):
        value = func(*args, **kwargs)
        if "," in value:
            values = [x.strip() for x in value.split(',')]
            try:
                return [float(item) for item in values]
            except ValueError:
                return values
        return value

    return wrapper


def get_file_settings(key: str) -> str:
    return config["FILE"][key]


@float_parser_decorator
@list_parser_decorator
def get_pointcloud_settings(key: str) -> Union[str, float, List]:
    return config["POINTCLOUD"][key]


@float_parser_decorator
@list_parser_decorator
def get_label_settings(key: str) -> Union[str, float, List]:
    return config["LABEL"][key]


@float_parser_decorator
@list_parser_decorator
def get_app_settings(key: str) -> str:
    return config["SETTINGS"][key]
