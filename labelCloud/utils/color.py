import colorsys

import numpy as np
import numpy.typing as npt
import pkg_resources


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
) -> np.ndarray:
    palette = np.loadtxt(
        pkg_resources.resource_filename("labelCloud.resources", "rocket-palette.txt")
    )
    palette_len = len(palette) - 1

    colors = np.zeros(points.shape)
    for ind, height in enumerate(points[:, 2]):
        colors[ind] = palette[round((height - z_min) / (z_max - z_min) * palette_len)]
    return colors.astype(np.float32)
