from pathlib import Path

from setuptools import setup

this_directory = Path(__file__).parent
README = (this_directory / "README.md").read_text()


setup(
    name="labelCloud",
    version="0.6.4",
    description="A lightweight tool for labeling 3D bounding boxes in point clouds.",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Christoph Sager",
    author_email="christoph.sager@gmail.com",
    url="https://github.com/ch-sa/labelCloud",
    license="GNU Geneal Public License v3.0",
    packages=[
        "labelCloud",
        "labelCloud.control",
        "labelCloud.definitions",
        "labelCloud.label_formats",
        "labelCloud.labeling_strategies",
        "labelCloud.model",
        "labelCloud.ressources.icons",
        "labelCloud.ressources.interfaces",
        "labelCloud.ressources",
        "labelCloud.tests",
        "labelCloud.utils",
        "labelCloud.view",
    ],
    package_data={
        "labelCloud.ressources": ["*"],
        "labelCloud.ressources.icons": ["*"],
        "labelCloud.ressources.interfaces": ["*"],
    },
    entry_points={"console_scripts": ["labelCloud=labelCloud.__main__:main"]},
    install_requires=[
        "numpy~=1.21.4",
        "open3d~=0.14.1",
        "PyOpenGL~=3.1.5",
        "PyQt5~=5.14.1",
    ],
    extras_require={
        "tests": [
            "pytest~=6.2.4",
            "pytest-qt~=4.0.2",
        ],
    },
    zip_safe=False,
    keywords="labelCloud",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Multimedia :: Graphics :: Viewers",
    ],
)
