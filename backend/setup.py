from setuptools import setup, find_packages

setup(
    name="fittrack-cli",
    version="0.1.0",
    packages=find_packages(),
    py_modules=["fittrack"],
    install_requires=[
        "httpx>=0.27.0",
        "click>=8.1.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "fittrack=fittrack:main",
        ],
    },
    python_requires=">=3.10",
)