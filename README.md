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

## Usage

### Labeling


### Shortcuts
