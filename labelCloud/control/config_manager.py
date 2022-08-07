"""Load configuration from .ini file."""
import configparser
from pathlib import Path
from typing import List, Union

import pkg_resources


class ExtendedConfigParser(configparser.ConfigParser):
    """Extends the ConfigParser with the ability to read and parse lists.

    Can automatically parse float values besides plain strings.
    """

    def getlist(
        self, section, option, raw=False, vars=None, fallback=None
    ) -> Union[List[str], List[float], str]:
        raw_value = self.get(section, option, raw=raw, vars=vars, fallback=fallback)
        if "," in raw_value:
            values = [x.strip() for x in raw_value.split(",")]
            try:
                return [float(item) for item in values]
            except ValueError:
                return values
        return raw_value

    def getpath(self, section, option, raw=False, vars=None, fallback=None) -> Path:
        """Get a path from the configuration file."""
        return Path(self.get(section, option, raw=raw, vars=vars, fallback=fallback))


class ConfigManager(object):
    PATH_TO_CONFIG = Path.cwd().joinpath("config.ini")
    PATH_TO_DEFAULT_CONFIG = Path(
        pkg_resources.resource_filename("labelCloud.resources", "default_config.ini")
    )

    def __init__(self) -> None:
        self.config = ExtendedConfigParser(comment_prefixes="/", allow_no_value=True)
        self.read_from_file()

    def read_from_file(self) -> None:
        if ConfigManager.PATH_TO_CONFIG.is_file():
            self.config.read(ConfigManager.PATH_TO_CONFIG)
        else:
            self.config.read(ConfigManager.PATH_TO_DEFAULT_CONFIG)

    def write_into_file(self) -> None:
        with ConfigManager.PATH_TO_CONFIG.open("w") as configfile:
            self.config.write(configfile, space_around_delimiters=True)

    def reset_to_default(self) -> None:
        self.config.read(ConfigManager.PATH_TO_DEFAULT_CONFIG)

    def get_file_settings(self, key: str) -> str:
        return self.config["FILE"][key]


config_manager = ConfigManager()
config = config_manager.config
