import logging
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Set, Tuple

import numpy as np

from ...utils.logger import blue
from ...utils.singleton import SingletonABCMeta

if TYPE_CHECKING:
    from ...model import PointCloud


class BasePointCloudHandler(object, metaclass=SingletonABCMeta):
    EXTENSIONS: Set[str] = set()  # should be set in subclasses

    @abstractmethod
    def read_point_cloud(self, path: Path) -> Tuple[np.ndarray, Optional[np.ndarray]]:  # type: ignore
        """Read a point cloud file and return only the points and colors as array."""
        logging.info(
            blue("Loading point cloud from %s using %s."), path, self.__class__.__name__
        )
        pass

    @abstractmethod
    def write_point_cloud(self, path: Path, pointcloud: "PointCloud") -> None:
        logging.info(
            blue("Writing point cloud to %s using %s."), path, self.__class__.__name__
        )
        pass

    @classmethod
    def get_supported_extensions(cls) -> Set[str]:
        return set().union(*[handler.EXTENSIONS for handler in cls.__subclasses__()])

    @classmethod
    def get_handler(cls, file_extension: str) -> "BasePointCloudHandler":
        """Return a point cloud handler for the given file extension."""
        for subclass in cls.__subclasses__():
            if file_extension in subclass.EXTENSIONS:
                return subclass()

        raise ValueError(
            "No point cloud handler found for file extension %s.", file_extension
        )
