import os
import pickle
import sys
from importlib import import_module
from pathlib import Path


def collect(benchmark_path: str, commit: str, cache_dir: str, venv_dir: str = None):
    benchmark = Path(benchmark_path).resolve()
    if not benchmark.is_file or benchmark.suffix != ".py":
        raise RuntimeError(f"Benchmark '{benchmark_path}' is not a valid Python file!")

    if venv_dir is not None:
        print(f"Activating venv for collection...")
        activation_script = str(Path(venv_dir).resolve() / "bin" / "activate_this.py")

        exec(open(activation_script).read(), {"__file__": activation_script})

    print(f"Collecting benchmarks for commit '{commit}'...")

    root_dir = benchmark.parent

    try:
        print(f"Running benchmark: {benchmark.stem} ...")

        sys.path.insert(0, str(root_dir))
        module = import_module(benchmark.stem)
        sys.path.pop(0)

        results = module.run()

    except Exception as e:
        print(f"Failed to run benchmark '{benchmark.stem}' with error: {e}")

    else:
        print(f"Results: {results}")
        cache = Path(cache_dir).resolve()
        print(f"Storing benchmark data in {cache}...")
        storage = cache / f"{commit}_{benchmark.stem}.pickle"
        if storage.exists():
            raise RuntimeError(f"Benchmark storage already existing! {storage}")
        storage.parent.mkdir(parents=True, exist_ok=True)
        with storage.open("wb") as f:
            pickle.dump(results, f)


if __name__ == "__main__":
    collect(*sys.argv[1:])
