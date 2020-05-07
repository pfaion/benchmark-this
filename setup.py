from setuptools import setup, find_packages

install_requires = [
    "gitpython",
    "matplotlib",
    "pandas",
    "rich",
    "virtualenv",
]

setup(
    authos="Patrick Faion",
    entry_points={"console_scripts": ["benchmark-this=benchmark_this.cli:main"]},
    install_requires=install_requires,
    name="benchmark-this",
    packages=find_packages(),
    version="0.0.0",
)
