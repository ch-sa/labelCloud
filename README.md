<p align="center">
    <img src="https://img.shields.io/badge/contributions-welcome!-green" alt="Contributions welcome!"/>
    <img src="https://img.shields.io/github/last-commit/ch-sa/labelCloud?color=blue">
    <img src="https://img.shields.io/pypi/pyversions/labelCloud" />
    <img src="https://github.com/ch-sa/labelCloud/workflows/Tests/badge.svg" />
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" />
</p>


# labelCloud
A lightweight tool for labeling 3D bounding boxes in point clouds.

![Overview of the Labeling Tool](https://raw.githubusercontent.com/ch-sa/labelCloud/master/docs/io_overview.png)

:new: *labelCloud is now [part of the PyPI](https://pypi.org/project/labelCloud/) and can be installed via pip!*

:new: *We are currently evaluating labelCloud and invite you to fill this questionaire https://forms.gle/moEyjGSa1Eiiq7VT8 (~5 min)!*

## Setup
:information_source: *Currently labelCloud supports Python 3.6 to 3.9.*

### via pip (PyPI)
```bash
pip install labelCloud
labelCloud --example  # start labelCloud with example point cloud
```

### via git (manually)

```bash
git clone https://github.com/ch-sa/labelCloud.git  # 1. Clone repository
pip install -r requirements.txt  # 2. Install requirements
# 3. Copy point clouds into `pointclouds` folder.
python3 labelCloud.py  # 4. Start labelCloud
```

Configure the software to your needs by editing the `config.ini` file or settings according to the [docs](https://github.com/ch-sa/labelCloud/blob/master/docs/documentation.md).

## Labeling
labelCloud supports two different ways of labeling (*picking* & *spanning*) as well as multiple mouse and keyboard options for subsequent correction.

![Screencast of the Labeling Methods](https://raw.githubusercontent.com/ch-sa/labelCloud/master/docs/screencast_small.gif)
(See also https://www.youtube.com/watch?v=8GF9n1WeR8A for a short introduction and preview of the tool.)

**Picking Mode**

* Pick the location of the bounding box (front-top edge)
* Adjust the z-rotation by scrolling with your mouse wheel

**Spanning Mode**

* Subsequently span the length, width and height of the bounding box by selecting four vertices
* The layers for for the last two vertices (width & height) will be locked to allow easy selection

**Correction**

* Use the buttons on the left-hand side or shortcuts to correct the *translation*, *dimension* and *rotation* of the bounding box
* Resize the bounding box by holding your cursor above one side and scrolling with the mouse wheel

By default the x- and y-rotation of bounding boxes will be prohibited.
For labeling **9 DoF-Bounding Boxes** deactivate `z-Rotation Only Mode` in the menu, settings or `config.ini` file.
Now you will be free to rotate around all three axes.

## Import & Export Options
labelCloud is built for a versatile use and aims at supporting all common point cloud file formats and label formats for storing 3D bounding boxes.
The tool is designed to be easily adaptable to multiple use cases. To change the settings, simply edit the corresponding line in the `config.ini` (see the [documentation](https://github.com/ch-sa/labelCloud/blob/master/docs/documentation.md)) for a description of all parameters).

**Supported Import Formats**

| Type      | File Formats                          |
| --------- | ------------------------------------- |
| Colored   | `*.pcd`, `*.ply`, `*.pts`, `*.xyzrgb` |
| Colorless | `*.xyz`, `*.xyzn`, `*.bin` (KITTI)    |

**Supported Export Formats**

| Label Format          | Description                                                                                                                                                    |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `centroid_rel`        | Centroid `[x, y, z]`; Dimensions `[length, width, height]`; <br> Relative Rotations as Euler angles in radians (-pi..+pi) `[yaw, pitch, roll]`                 |
| `centroid_abs`        | Centroid `[x, y, z]`; Dimensions `[length, width, height]`; <br> Absolute Rotations as Euler angles in degrees (0..360°) `[yaw, pitch, roll]`                  |
| `vertices`            | 8 Vertices of the bounding box each with `[x, y, z]` (see [documentation.md](https://github.com/ch-sa/labelCloud/blob/master/docs/documentation.md) for order) |
| `kitti`               | Centroid; Dimensions; z-Rotation (See [specification](https://github.com/bostondiditeam/kitti/blob/master/resources/devkit_object/readme.txt))                 |
| `kitti_untransformed` | See above, but without transformations.                                                                                                                        |

You can easily create your own exporter by subclassing the abstract [BaseLabelFormat](https://github.com/ch-sa/labelCloud/blob/master/labelCloud/label_formats/base.py#L10).
All rotations are counterclockwise (i.e. a z-rotation of 90°/π is from the positive x- to the negative y-axis!).

## Shortcuts

|                               Shortcut                               | Description                                          |
| :------------------------------------------------------------------: | ---------------------------------------------------- |
|                             *Navigation*                             |                                                      |
|                          Left Mouse Button                           | Rotates the Point Cloud                              |
|                          Right Mouse Button                          | Translates the Point Cloud                           |
|                             Mouse Wheel                              | Zooms into the Point Cloud                           |
|                             *Correction*                             |                                                      |
|         `W`, `A`, `S`, `D` <br> `Ctrl` + Right Mouse Button          | Translates the Bounding Box back, left, front, right |
|                               `Q`, `E`                               | Lifts the Bounding Box up, down                      |
|                               `X`, `Y`                               | Rotates the Boundign Box around z-Axis               |
| Scrolling with the Cursor above a Bounding Box Side ("Side Pulling") | Changes the Dimension of the Bounding Box            |
|                         `C` & `V`, `B` & `N`                         | Rotates the Bounding Box around y-Axis, x-Axis       |
|                              *General*                               |                                                      |
|                                `Del`                                 | Deletes Current Bounding Box                         |
|                                 `R`                                  | Resets Perspective                                   |
|                                `Esc`                                 | Cancels Selected Points                              |


See [documentation.md](https://github.com/ch-sa/labelCloud/blob/master/docs/documentation.md) for software conventions.

## Usage & Attribution
When using the tool feel free to drop me a mail with feedback or a description of your use case (christoph.sager[at]tu-dresden.de).
If you are using the tool for a scientific project please consider citing our [pending publication](https://arxiv.org/abs/2103.04970):

    # forthcoming
    @article{sager_2021,
      title={labelCloud: A Lightweight Domain-Independent Labeling Tool for 3D Object Detection in Point Clouds},
      journal={Computer-Aided Design and Applications},
      author={Sager, Christoph and Zschech, Patrick and Kühl, Niklas},
      year={2021}}
   
    # published
    @misc{sager2021labelcloud,
      title={labelCloud: A Lightweight Domain-Independent Labeling Tool for 3D Object Detection in Point Clouds}, 
      author={Christoph Sager and Patrick Zschech and Niklas Kühl},
      year={2021},
      eprint={2103.04970},
      archivePrefix={arXiv},
      primaryClass={cs.CV}
    }

## Acknowledgment
I would like to thank the [Robotron RCV-Team](https://www.robotron.de/rcv) for the support in the preparation and user evaluation of the software.
The software was developed as part of my diploma thesis titled "labelCloud: Development of a Labeling Tool for 3D Object Detection in Point Clouds" at the [Chair for Business Informatics, especially Intelligent Systems](https://tu-dresden.de/bu/wirtschaft/winf/isd) of the TU Dresden. The ongoing research can be followed in our [project on ResearchGate](https://www.researchgate.net/project/Development-of-a-Point-Cloud-Labeling-Tool-to-Generate-Training-Data-for-3D-Object-Detection-and-6D-Pose-Estimation).
