from distutils.core import setup

setup(
    name="labelCloud",
    version="0.1.0",
    author="Christoph Sager",
    author_email="christoph.sager@gmail.com",
    packages=["labelCloud"],
    license="Creative Commons Attribution-Noncommercial license",
    description="labelCloud is a graphical annotation tool to label 3D bounding boxes in point "
    "clouds",
    long_description=open("README.md").read(),
    install_requires=[
        "numpy~=1.21.2",
        "open3d~=0.13.0",
        "PyOpenGL~=3.1.5",
        "PyQt5~=5.15.4",
    ],
    extras_require={
        "tests": [
            "pytest~=6.2.4",
            "pytest-qt~=4.0.2",
        ],
    },
    entry_points={"console_scripts": ["labelCloud=labelCloud:main"]},
)
