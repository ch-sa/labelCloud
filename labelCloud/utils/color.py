import colorsys

import numpy as np
import numpy.typing as npt


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
                ),
                dtype=np.float32,
            )
            for value in range(0, n)
        ]
    )
