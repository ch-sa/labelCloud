from distutils.core import setup

setup(
    name='labelCloud',
    version='0.1.0',
    author="Christoph Sager",
    author_email="christoph.sager@gmail.com",

    packages=['labelCloud'],
    license='Creative Commons Attribution-Noncommercial license',
    description='labelCloud is a graphical annotation tool to label 3D bounding boxes in point clouds',
    long_description=open('README.md').read(),

    install_requires=[
        "numpy~=1.19.4",
        "PyQt5~=5.15.2",
        "PyOpenGL~=3.1.5",
        "open3d~=0.11.2"
    ],
)