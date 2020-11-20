<p align="center">
    <img src="https://img.shields.io/badge/contributions-welcome!-green" alt="Contributions welcome!"/>
    <img src="https://img.shields.io/github/last-commit/ch-sa/labelCloud?color=blue">
    <img src="https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue" />
</p>


# labelCloud
A lightweight tool for labeling 3D bounding boxes in point clouds.

![Overview of the Labeling Tool](docs/io_overview.png)

## Labeling
labelCloud supports two different ways of labeling (*picking* & *spanning*) as well as multiple mouse and keyboard options for subsequent correction.

![Screencast of the Labeling Methods](docs/screencast_small.gif)

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

## Import & Export Options
labelCloud is built for a versatile use and aims at supporting all common point cloud and 3DOD-label formats.

**Supported Import Formats**
* `*.pcd`, `*.ply`, `*.pts`
* `*.xyz`, `*.xyzn`, `*.xyzrgb`
* `*.bin` (KITTI) → [x, y, z, reflectance]

Colored and colorless point clouds can be visualized.

**Supported Export Formats**

| Label Format | Description |
| --- | --- |
| `centroid_rel` | Centroid `[x, y, z]`; Dimensions `[length, width, height]`; <br> Relative Rotations as Euler angles in radians (-pi..+pi) `[yaw, pitch, roll]` |
| `centroid_abs` | Centroid `[x, y, z]`; Dimensions `[length, width, height]`; <br> Absolute Rotations as Euler angles in degrees (0..360°) `[yaw, pitch, roll]` |
| `vertices` | 8 Vertices of the bounding box each with `[x, y, z]` |
| `kitti` | Centroid; Dimensions; z-Rotation (See [specification](https://github.com/bostondiditeam/kitti/blob/master/resources/devkit_object/readme.txt)) |
| `votenet` | *Coming soon!* |

You can easily create your own exporter by implementing the [IFormattingInterface](https://github.com/ch-sa/labelCloud/blob/4700915f9c809c827544f08e09727f4755545d73/modules/control/label_manager.py#L94).
All rotations are counterclockwise (i.e. a z-rotation of 90°/π is from the positive x- to the negative y-axis!).

## Setup

1. Clone repository: `git clone https://github.com/ch-sa/labelCloud.git`.
2. Install requirements: `pip install -r requirements.txt`.
3. Copy point clouds into `pointclouds` folder.
4. Run `python3 labelCloud.py`.

## Shortcuts

| Shortcut | Description |
| :---: | --- |
| *Navigation* | |
| Left Mouse Button | Rotate the Point Cloud |
| Right Mouse Button | Translate the Point Cloud |
| Mouse Wheel | Zoom into the Point Cloud |
| *Correction* | |
| `W`, `A`, `S`, `D` <br> `Ctrl` + Right Mouse Button | Translate BBox back, left, front, right |
| `Q`, `E` | Lift BBox up, down |
| `X`, `Y` | Rotate BBox around z-Axis |
| Scrolling with Cursor above BBox Side | Side Pulling (Change Dimensions) |
|`C` & `V`, `B` & `N` | Rotate BBox around y-Axis, x-Axis |
| *General* | |
| `Del` | Delete Current BBox |
| `R` | Reset Perspective |
| `Esc` | Chancel Selected Points |
