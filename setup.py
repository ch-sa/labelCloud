from pathlib import Path

from setuptools import setup

this_directory = Path(__file__).parent
README = (this_directory / "README.md").read_text()


setup(
    name="labelCloud",
    version="0.6.5",
    description="A lightweight tool for labeling 3D bounding boxes in point clouds.",
    long_description=README,
    long_description_content_type="text/markdown",
    maintainer="Christoph Sager",
    maintainer_email="christoph.sager@gmail.com",
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
        "numpy",
        "open3d",
        "PyOpenGL",
        "PyQt5 <= 5.14.1;platform_system=='Windows'",  # avoids PyQt5 incompatibility on windows
        "PyQt5;platform_system!='Windows'",
    ],
    extras_require={
        "tests": [
            "pytest",
            "pytest-qt",
        ],
    },
    zip_safe=False,
    keywords=[
        "labelCloud",
        "machine learning",
        "computer vision",
        "annotation tool",
        "labeling",
        "point clouds",
        "bounding boxes",
        "3d object detection",
        "6d pose estimation",
    ],
    python_requires=">=3.6",
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
    project_urls={
        "GitHub": "https://github.com/ch-sa/labelCloud",
        "YouTube Demo": "https://www.youtube.com/watch?v=8GF9n1WeR8A",
        "Publication": "https://arxiv.org/abs/2103.04970",
    },
)
