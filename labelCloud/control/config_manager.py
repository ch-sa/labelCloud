"""Load configuration from .ini file."""
import configparser

# Read local file `config.ini`.
import os
from typing import List, Union


# Parses string to list if it contains a ","
def bool_float_parser_decorator(func):
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


class ConfigManager(object):
    PATH_TO_CONFIG = "config.ini"

    def __init__(self):
        self.config = configparser.ConfigParser(comment_prefixes='/', allow_no_value=True)
        self.read_from_file()

    def read_from_file(self):
        if os.path.isfile(ConfigManager.PATH_TO_CONFIG):
            self.config.read(ConfigManager.PATH_TO_CONFIG)
        else:
            self.config.read("ressources/default_config.ini")

    def write_into_file(self):
        with open(ConfigManager.PATH_TO_CONFIG, 'w') as configfile:
            self.config.write(configfile, space_around_delimiters=True)

    def get_file_settings(self, key: str) -> str:
        return self.config["FILE"][key]

    @bool_float_parser_decorator
    @list_parser_decorator
    def get_pointcloud_settings(self, key: str) -> Union[str, float, List]:
        return self.config["POINTCLOUD"][key]

    @bool_float_parser_decorator
    @list_parser_decorator
    def get_label_settings(self, key: str) -> Union[str, float, List]:
        return self.config["LABEL"][key]

    @bool_float_parser_decorator
    @list_parser_decorator
    def get_app_settings(self, key: str) -> str:
        return self.config["USER_INTERFACE"][key]


config = ConfigManager()
