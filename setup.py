#!/usr/bin/env python3
"""Setup script for gradik."""
from setuptools import setup, find_packages
from pathlib import Path

# Read version from VERSION file
def get_version():
    version_file = Path(__file__).parent / 'VERSION'
    if version_file.exists():
        return version_file.read_text().strip()
    return '0.0.0'

setup(
    name='gradik',
    version=get_version(),
    description='Lightweight web dashboard to monitor and kill Gradle daemons, Kotlin, Android Studio, and IDE processes.',
    author='onelenyk',
    url='https://github.com/onelenyk/gradik',
    packages=find_packages(),
    py_modules=['app'],
    install_requires=[
        'flask==3.0.0',
        'psutil==5.9.7',
    ],
    entry_points={
        'console_scripts': [
            'gradik=app:main',
        ],
    },
    python_requires='>=3.8',
)
