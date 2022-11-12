import numpy as np

from labelCloud.utils.color import colorize_points_with_height, get_distinct_colors


def test_get_distinct_colors() -> None:
    num_colors = 17
    colors = get_distinct_colors(num_colors)
    assert isinstance(colors[0], str)
    assert len(colors) == num_colors


def test_colorize_points_with_height() -> None:
    num_points = 900
    points = np.random.uniform(low=0, high=10, size=(num_points, 3))
    z_min = points[:, 2].min()
    z_max = points[:, 2].max()

    colors = colorize_points_with_height(points, z_min, z_max)
    assert colors.dtype == np.float32
    assert colors.shape == (num_points, 3)
    assert 0 <= colors.max() <= 1
