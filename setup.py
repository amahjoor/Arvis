"""
Setup script for Arvis Room Intelligence System.
"""

from setuptools import setup, find_packages

setup(
    name="arvis",
    version="0.1.0",
    description="Arvis Room Intelligence System",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        # Dependencies are in requirements.txt
    ],
    entry_points={
        "console_scripts": [
            "arvis=src.main:cli_main",
        ],
    },
)

