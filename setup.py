from setuptools import setup, find_packages
import json

setup(
    name="priority-living-cli",
    version="3.1.0",
    description="Priority Living CLI — Sovereign AI command & control for your local machine",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Priority Living Labs",
    url="https://prioritylivinglabs.lovable.app",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[],
    extras_require={
        "ai": ["torch", "transformers", "huggingface_hub"],
    },
    entry_points={
        "console_scripts": [
            "pl=priority_living.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
