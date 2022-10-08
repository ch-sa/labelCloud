# Conventions

## Coordinate System

The point cloud is rendered in a right-handed coordinate system (see [OpenGL description](https://learnopengl.com/Getting-started/Coordinate-Systems)).

## Bounding Boxes

The bounding box is internally represented with a centroid, three dimensions and absolute rotations in Euler angles.
Rotations are counter-clockwise and inside 0° and 360°.
The initial bounding box is oriented with the x-axis representing the length of the object.
The bounding box vertices are ordered clockwise from bottom to top starting at the origin.
The sequence is adopted from the [bbox library](https://varunagrawal.github.io/bbox/bbox.html#module-bbox.bbox3d).

| Point | Position (x, y, z) |
| :---: | ------------------ |
|   0   | left back bottom   |
|   1   | left front bottom  |
|   2   | right front bottom |
|   3   | right back bottom  |
|   4   | left back top      |
|   5   | left front top     |
|   6   | right front top    |
|   7   | right back top     |

If the `vertices` label format is selected, the points will get exported in a list in this sequence.
When labelCloud shows the orientation, the arrow points at the right side of the bounding box (2, 3, 6, 7) and upwards (6, 7).

