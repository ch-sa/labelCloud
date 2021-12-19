# Documentation of labelCloud

## Software Principles

### Coordinate System

The point cloud is rendered in a right-handed coordinate system (see [OpenGL description](https://learnopengl.com/Getting-started/Coordinate-Systems)).

### Bounding Boxes

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

## Configuration

The settings of labelCloud can be changed using the config file (`config.ini`) and for most options exists an entry in the graphical settings (accesible via the menu).
The following parameters can be changed:

|          Parameter          | Description                                                                                     |   Default/ Example    |
| :-------------------------: | ----------------------------------------------------------------------------------------------- | :-------------------: |
|         **[FILE]**          |
|     `pointcloud_folder`     | Folder from which the point cloud files are loaded.                                             |    *pointclouds/*     |
|       `label_folder`        | Folder where the label files will be saved.                                                     |       *labels/*       |
|       `image_folder`        | Folder from which related images can be loaded (OPTIONAL).                                      |    *pointclouds/*     |
|      **[POINTCLOUD]**       |
|        `point_size`         | Drawing size for points in point cloud (rasterized diameter).                                   |          *4*          |
|      `colorless_color`      | Point color for colorless point clouds (r,g,b).                                                 |    *0.9, 0.9, 0.9*    |
|    `colorless_colorize`     | Colerize colorless point clouds by height value.                                                |        *True*         |
|      `std_translation`      | Standard step for point cloud translation (with mouse move).                                    |        *0.03*         |
|         `std_zoom`          | Standard step for zooming (with mouse scroll).                                                  |       *0.0025*        |
|         **[LABEL]**         |
|       `label_format`        | Format for exporting labels, choose from `vertices`, `centroid_rel`, `centroid_abs` or `kitti`. |    *centroid_abs*     |
|      `object_classes`       | List of object classes for autocompletion in the class text field.                              | *class1, class2, ...* |
|     `std_object_class`      | Default object class for new bounding boxes.                                                    |    *default_class*    |
|     `export_precision`      | Number of decimal places for exporting the bounding box parameters.                             |          *8*          |
|  `std_boundingbox_length`   | Default length of the bounding box (for picking mode).                                          |        *0.75*         |
|   `std_boundingbox_width`   | Default width of the bounding box (for picking mode).                                           |        *0.55*         |
|  `std_boundingbox_height`   | Default height of the bounding box (for picking mode).                                          |        *0.15*         |
|      `std_translation`      | Standard step for translating the bounding box (with key or button press).                      |        *0.03*         |
|       `std_rotation`        | Standard step for rotating the bounding box (with key press).                                   |         *0.5*         |
|        `std_scaling`        | Standard step for scaling the bounding box (with button press).                                 |        *0.03*         |
| `min_boundingbox_dimension` | Minimum value for the length, width and height of a bounding box.                               |        *0.01*         |
|    **[USER_INTERFACE]**     |
|      `z_rotation_only`      | Only allow z-rotation of bounding box; deactivate to also label x- & y-rotation.                |        *True*         |
|        `show_floor`         | Visualizes the floor (x-y-plane) as a grid.                                                     |        *True*         |
|     `show_orientation`      | Visualizes the object's orientation as an arrow.                                                |        *True*         |
|     `background_color`      | Background color of the point cloud viewer (rgb).                                               |    *100, 100, 100*    |
|     `viewing_precision`     | Number of decimal places shown on the right side for the parameters of the active bounding box. |          *3*          |
|        `near_plane`         | Min. distance of objects to be displayed by OpenGL                                              |         *0.1*         |
|         `far_plane`         | Max. distance of objects to be displayed by OpenGL                                              |         *300*         |
|     `keep_perspective`      | Save last perspective when leaving a point cloud                                                |        *False*        |
|       `show_2d_image`       | Show button to visualize related images in a separate window                                    |        *False*        |
