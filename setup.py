import setuptools
import os

this_directory = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(this_directory, "README.md")
with open(readme_path, encoding="utf-8") as handle:
    long_description = handle.read()

requires = (
    "tqdm>=4.61.2",
)

setuptools.setup(
    name="spoonfed_commonvoice",
    version="0.0.4",
    author="Dallon Asnes",
    author_email="dallon.asnes@gmail.com",
    description="CLI to generate Anki notes from Mozilla CommonVoice Datasets for language study",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dallonasnes/spoonfed-commonvoice",
    entry_points={
        "console_scripts": [
            "cva=spoonfed_commonvoice.main:run",
        ],
    },
    packages=setuptools.find_packages(),
    install_requires=requires,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)