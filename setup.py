import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="spoonfed-commonvoice",
    version="0.0.1",
    author="Dallon Asnes",
    author_email="dallon.asnes@email.com",
    description="CLI to generate Anki notes from Mozilla CommonVoice Datasets for language study",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dallonasnes/spoonfed-commonvoice",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: Do No Harm License",
        "Operating System :: OS Independent",
    ),
)