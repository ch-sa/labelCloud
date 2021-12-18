from setuptools import setup


setup(
    name="labelCloud",
    version="0.6.0",
    description="A lightweight tool for labeling 3D bounding boxes in point clouds.",
    long_description=open("README.md").read(),
    author="Christoph Sager",
    author_email="christoph.sager@gmail.com",
    url="https://github.com/ch-sa/labelCloud",
    license="GNU Geneal Public License v3.0",
    packages=[
        "labelCloud",
        "labelCloud.ressources",
        "labelCloud.ressources.icons",
        "labelCloud.tests",
        "labelCloud.control",
        "labelCloud.label_formats",
        "labelCloud.labeling_strategies",
        "labelCloud.model",
        "labelCloud.utils",
        "labelCloud.view",
    ],
    package_data={"labelCloud.ressources": ["*"], "labelCloud.ressources.icons": ["*"]},
    entry_points={"console_scripts": ["labelCloud=labelCloud.__main__:main"]},
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
    zip_safe=False,
    keywords="labelCloud",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
