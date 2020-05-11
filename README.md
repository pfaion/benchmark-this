# benchmark-this

Benchmark your code over the git history.

## Quickstart

**DISCLAIMER:** This is an alpha version. The public API will change a lot.

Currently only supports repositories that can be installed.

### Benchmarks
- Benchmarks are scripts that live in the corresponding repository.
- A benchmark needs a `run()` function that will be invoked.
- The `run()` function returns a dictionary of string to numerical values, think of it as basic labeled metrics.
- Currently the benchmark from the active commit will be run over the history, not historical benchmarks.

Here is an (obviously useless) example benchmark.

```python
# your_repo/benchmarks/test.py

import random

def run():
    return {
        "FPS": random.random(),
        "Error": random.random(),
    }
```

### Install

Install current development version of **benchmark-this** with pip:
```bash
pip install git+https://github.com/pfaion/benchmark-this.git
```

### CLI Usage

Run with:
```bash
cd path/to/your/repo
benchmark-this -p
```
This will run all benchmarks on the last 10 commits, cache the results (!) and print the resulting data. If you want some simple graphs tracking the benchmark results, use

```bash
benchmark-this -i .
```

This will e.g. create a `test.png` plot in the current folder for the `test.py` benchmark.

Currently supported options:

```
usage: benchmark-this [-h] [-r REPO] [-n N] [-l] [-c] [-p] [-i IMAGES] [-v] [benchmarks [benchmarks ...]]

Run benchmarks on a git repository.

positional arguments:
  benchmarks            list of benchmarks to run, omit to run all available benchmarks

optional arguments:
  -h, --help            show this help message and exit
  -r REPO, --repo REPO  the repository to benchmark (default: current working directory)
  -n N                  number of commits to benchmark (default: 10)
  -l, --list            enable to list available benchmarks and exit
  -c, --clear-cache     enable to overwrite existing benchmark caches
  -p, --print           enable to print outputs to console
  -i IMAGES, --images IMAGES
                        specify a path to store generic plots for the benchmarks
  -v, --verbose         enable to print verbose output
```

### Python Usage

You can also invoke benchmark-this from Python to get the results and do further processing, e.g. custom plots:

```python
from benchmark_this import Benchmarker

bench = Benchmarker(path="path/to/my/repo", n_commits=10)
bench.run()

results = bench.dataframes  # a list of one pandas dataframe per benchmark
```
