"""
Install script for PIPyAWC
"""
from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

setup(
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires="~=3.7",
    scripts=["bin/PiPy-AWC"],
)
