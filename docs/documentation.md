# Documentation of labelCloud

## Software Principles

### Coordinate System

The point cloud is rendered in a right-handed coordinate system (see [OpenGL describtion](https://learnopengl.com/Getting-started/Coordinate-Systems)).

### Bounding Boxes

The bounding box is interally represented with a centroid, three dimensions and absolute rotations in Euler angles.
Rotations are counter-clockwise and between 0° and 360°.
The initial bounding boxes is oriented with the x-axis representing the length.
The bounding box vertices are ordered clockwise from bottom to top starting at the origin.
The sequence is adopted from the [bbox library](https://varunagrawal.github.io/bbox/bbox.html#module-bbox.bbox3d).

| Point | Position (x, y, z)|
| :---: | --- |
| 0 | left back bottom |
| 1 | left front bottom |
| 2 | right front bottom |
| 3 | right back bottom |
| 4 | left back top |
| 5 | left front top |
| 6 | right front top |
| 7 | right back top |

If the `vertices` label format is selected, the points will get exported in a list in this sequence.
When labelCloud shows the orientation, the arrow points at the right side of the bounding box (2, 3, 6, 7) and upwards (6, 7).

## Configuration

The settings of labelCloud can currently only be changed using the config file (`config.ini`).
The following parameters can be changed:

| Parameter | Description | Default/ Example |
| :---: | --- | :---: |
| **[FILE]** |
| `POINTCLOUD_FOLDER` | Source of point clouds | *pointclouds/* |
| `LABEL_FOLDER`| Sink for label files | *labels/* |
| **[POINTCLOUD]** |
| `POINT_SIZE` | Drawing size for points in point cloud | *4* |
| `COLORLESS_COLOR` | Point color for colorless point clouds (r,g,b) | *0.9, 0.9, 0.9* |
| `COLORLESS_COLORIZE` | Colerize colorless point clouds by height value | *True* |
| `STD_TRANSLATION` | Standard step for point cloud translation | *0.03* |
| `STD_ZOOM` | Standard step for zooming | *0.0025* |
| **[LABEL]** |
| `LABEL_FORMAT` | Format for exporting labels. Choose from (`vertices`, `centroid_rel`, `centroid_abs`, `kitti`) | *centroid_abs* |
| `OBJECT_CLASSES` | List of object classes for autocompletion | *class1, class2, ...* |
| `STD_OBJECT_CLASS` | Default object class | *default_class* |
| `Z_ROTATION_ONLY` | Only allow z-rotation of bounding box. Deactivate to also label x- & y-rotation | *True* |
| `EXPORT_PRECISION` | Number of decimal places for export label. | *6* |
| `MIN_BOUNDINGBOX_DIMENSION` | Minimum bounding box dimension. | *0.01* |
| `STD_BOUNDINGBOX_LENGTH` | Default lenght of the bounding box (for picking mode) | *0.75* |
| `STD_BOUNDINGBOX_WIDTH` | Default width of the bounding box (for picking mode) | *0.55* |
| `STD_BOUNDINGBOX_HEIGHT`| Default height of the bounding box (for picking mode) | *0.15* |
| `STD_TRANSLATION`| Standard step for translating the bounding box | *0.03* |
| `STD_ROTATION` | Standard step for rotating the bounding box | *0.5* |
| `STD_SCALING` | Standard step for scaling the bounding box | *0.03* |
| **[SETTINGS]** |
| `BACKGROUND_COLOR` | Background color of the point cloud viewer (rgb) | *100, 100, 100* |
| `SHOW_FLOOR` | Visualizes the floor (x-y-plane) as a grid | *True* |
| `SHOW_ORIENTATION` | Visualizes the object's orientation as an arrow | *True* |
