# labelCloud
A lightweight tool for labeling 3D bounding boxes in point clouds.

![Overview of the Labeling Tool](docs/io_overview.png)


## Setup

1. Install requirements: `pip install -r requirements.txt`.
2. Copy point clouds into `pointclouds` folder.
3. Run `python3 labelCloud`.

## Import & Export Options
labelCloud is built for a versatile use and aims at supporting all common point cloud and 3DOD-label formats.

**Supported Import Formats**
* `*.pcd`, `*.ply`, `*.pts`
* `*.xyz`, `*.xyzn`, `*.xyzrgb`

Colored and colorless point clouds can be visualized.

**Supported Export Formats**

| Label Format | Description |
| --- | --- |
| Center | Centroid `[x, y, z]`; Dimensions `[length, width, height]`; Rotations as Euler angles in degrees `[yaw, pitch, roll]` |
| Vertices | 8 Vertices of the bounding box each with `[x, y, z]` |
| KITTI | Centroid; Dimensions; z-Rotation (See [specification](https://github.com/bostondiditeam/kitti/blob/master/resources/devkit_object/readme.txt)) |
| VoteNet | *Coming soon!* |

You can easily create your own exporter by implementing the [IFormattingInterface](https://github.com/ch-sa/labelCloud/blob/4700915f9c809c827544f08e09727f4755545d73/modules/control/label_manager.py#L94).

## Labeling
**Picking Mode**

* Pick the location of the bounding box (front-top edge)
* Adjust the z-rotation by scrolling with your mouse wheel

**Spanning Mode**

* Subsequently span the length, width and height of the bounding box by selecting four vertices
* The layers for for the last two vertices (width & height) will be locked to allow easy selection

**Correction**

* Use the buttons on the left-hand side or shortcuts to correct the *translation*, *dimension* and *rotation* of the bounding box

By default the x- and y-rotation of bounding boxes will be prohibited.
For labeling **9 DoF-Bounding Boxes** deactivate `z-Rotation Only Mode`.
Now you will be free to rotate around all three axes.

## Shortcuts

**Navigation**

| Shortcut | Description |
| :---: | --- |
| Left Mouse Button | Rotate the Point Cloud |
| Right Mouse Button | Translate the Point Cloud |
| Mouse Wheel | Zoom into the Point Cloud |

**Correction**

| Shortcut | Description|
| :---: | --- |
| `W`, `A`, `S`, `D` <br> `Ctrl` + Right Mouse Button | Translate BBox back, left, front, right |
| `Q`, `E` | Lift BBox up, down |
| `X`, `Y` | Rotate BBox around z-Axis |
| Scrolling with Cursor above BBox Side | Side Pulling (Change Dimensions) |
|`C` & `V`, `B` & `N` | Rotate BBox around x-Axis, y-Axis |

**General**

| Shortcut | Description|
| :---: | --- |
| `Del` | Delete Current BBox |
| `R` | Reset Perspective |
| `Esc` | Chancel Selected Points |
