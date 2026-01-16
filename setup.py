#!/usr/bin/env python3
"""Setup script for gradik."""
from setuptools import setup, find_packages

setup(
    name='gradik',
    version='1.0.0',
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
