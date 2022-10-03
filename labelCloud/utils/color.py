import colorsys

import pkg_resources

import numpy as np
import numpy.typing as npt

from ..definitions.types import Color4f


def get_distinct_colors(n: int) -> npt.NDArray[np.float32]:
    """generate visualy distinct colors
    Args:
        n (int): number of colors
    Returns:
        npt.NDArray[np.float32]: n x 3 (rgb) values between 0 and 1
    """
    hue_partition = 1.0 / (n + 1)
    return np.vstack(
        [
            np.array(
                colorsys.hsv_to_rgb(
                    hue_partition * value,
                    1.0 - (value % 2) * 0.5,
                    1.0 - (value % 3) * 0.1,
                )
            )
            for value in range(0, n)
        ]
    ).astype(np.float32)


def colorize_points_with_height(
    points: np.ndarray, z_min: float, z_max: float
) -> npt.NDArray[np.float32]:
    palette = np.loadtxt(
        pkg_resources.resource_filename("labelCloud.resources", "rocket-palette.txt")
    )
    palette_len = len(palette) - 1

    colors = np.zeros(points.shape)
    for ind, height in enumerate(points[:, 2]):
        colors[ind] = palette[round((height - z_min) / (z_max - z_min) * palette_len)]
    return colors.astype(np.float32)


def hex_to_rgba(hex: str) -> Color4f:
    """Converts a hex color to a list of RGBA values.

    Args:
        hex (str): The hex color to convert.

    Returns:
        List[float]: The RGBA values.
    """
    hex = hex.lstrip("#")

    if len(hex) == 6:
        hex = hex + "ff"

    return tuple(  # type: ignore
        [int(hex[i : i + 2], 16) / 255 for i in range(0, 8, 2)]
    )


def rgba_to_hex(color: Color4f) -> str:
    """Converts a list of RGBA values to a hex color.

    Args:
        color (Color4f): The RGBA values.

    Returns:
        str: The hex color.
    """
    return "#%02x%02x%02x%02x" % tuple([int(c * 255) for c in color])
