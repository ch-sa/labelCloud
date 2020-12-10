<p align="center">
    <img src="https://img.shields.io/badge/contributions-welcome!-green" alt="Contributions welcome!"/>
    <img src="https://img.shields.io/github/last-commit/ch-sa/labelCloud?color=blue">
    <img src="https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue" />
</p>


# labelCloud
A lightweight tool for labeling 3D bounding boxes in point clouds.

![Overview of the Labeling Tool](docs/io_overview.png)

## Setup

1. Clone repository: `git clone https://github.com/ch-sa/labelCloud.git`.
2. Install requirements: `pip install -r requirements.txt`.
3. Copy point clouds into `pointclouds` folder.
4. Run `python3 labelCloud.py`.

## Labeling
labelCloud supports two different ways of labeling (*picking* & *spanning*) as well as multiple mouse and keyboard options for subsequent correction.

![Screencast of the Labeling Methods](docs/screencast_small.gif)
(See also https://www.youtube.com/watch?v=8GF9n1WeR8A for a short introduction and preview of the tool.)

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
labelCloud is built for a versatile use and aims at supporting all common point cloud file formats and label formats for storing 3D bounding boxes.

**Supported Import Formats**
| Type | File Formats |
| --- | --- |
| Colored | `*.pcd`, `*.ply`, `*.pts`, `*.xyzrgb` |
| Colorless | `*.xyz`, `*.xyzn`, `*.bin` (KITTI)  |

**Supported Export Formats**

| Label Format | Description |
| --- | --- |
| `centroid_rel` | Centroid `[x, y, z]`; Dimensions `[length, width, height]`; <br> Relative Rotations as Euler angles in radians (-pi..+pi) `[yaw, pitch, roll]` |
| `centroid_abs` | Centroid `[x, y, z]`; Dimensions `[length, width, height]`; <br> Absolute Rotations as Euler angles in degrees (0..360°) `[yaw, pitch, roll]` |
| `vertices` | 8 Vertices of the bounding box each with `[x, y, z]` (see [documentation.md](docs/documentation.md) for order) |
| `kitti` | Centroid; Dimensions; z-Rotation (See [specification](https://github.com/bostondiditeam/kitti/blob/master/resources/devkit_object/readme.txt)) |
| `votenet` | *Coming soon!* |

You can easily create your own exporter by implementing the [IFormattingInterface](https://github.com/ch-sa/labelCloud/blob/4700915f9c809c827544f08e09727f4755545d73/modules/control/label_manager.py#L94).
All rotations are counterclockwise (i.e. a z-rotation of 90°/π is from the positive x- to the negative y-axis!).

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


See [documentation.md](docs/documentation.md) for software conventions.

## Usage & Attribution
When using the tool feel free to drop me a mail with feedback or a description of your use case (christoph.sager[at]tu-dresden.de).

If you are using the tool for a scientific project please think about citing:


    @MastersThesis{sager_2020,
        title={labelCloud: Development of a Labeling Tool for 3D Object Detection in Point Clouds},
        url={https://github.com/ch-sa/labelCloud/},
        author={Sager, Christoph},
        year={2020}}
