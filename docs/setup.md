# Setup

## Installation
!!! info Python Support
    Currently labelCloud supports Python 3.7 to 3.9.

### via pip (PyPI)

Simply install the latest version using pip.

``` sh
pip install labelCloud
labelCloud --example  # start labelCloud with example point cloud
```

The `labelCloud` command is now globally available.

### via git (manually)

Clone this repository and run labelCloud with Python.

```sh
git clone https://github.com/ch-sa/labelCloud.git  # 1. Clone repository
pip install -r requirements.txt  # 2. Install requirements
# 3. Copy point clouds into `pointclouds` folder.
python3 labelCloud.py  # 4. Start labelCloud
```

## Folder Structure

labelCloud expects a certain folder structure with pre-defined names.
These can be changed in the `config.ini`.


```sh
my_project/                 # project folder
├── config.ini              # project configuration
├── labels                  # label folder
│   ├── _classes.json       # label configuration (names, colors)
│   ├── pcd_01.json
│   ├── pcd_02.json
│   └── ...
└── pointclouds             # point cloud folder
    ├── pcd_01.ply
    ├── pcd_02.ply
    └── ...
```

Configure the software to your needs by editing the `config.ini` file or settings (see [Configuration](configuration.md)).