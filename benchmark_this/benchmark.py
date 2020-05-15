import os
import pickle
import shutil
import subprocess
import sys
from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List

import pandas as pd
import virtualenv
from git import Commit, Repo
from matplotlib import pyplot as plt
from rich.console import Console

from . import collector

console = Console()
rprint = console.print


class Benchmarker:
    def __init__(self, path: str, n_commits: int):
        self.path = Path(path).resolve()
        if not self.path.is_dir():
            raise NotADirectoryError(f"Repository path does not exist: '{self.path}'")

        self.repo = Repo(str(self.path))

        self.benchmark_dir = self.path / "benchmarks"
        self.data_dir = self.benchmark_dir / "__benchmark_data__"
        if not self.benchmark_dir.is_dir():
            raise NotADirectoryError(
                f"Benchmark directory does not exist: '{self.path}'"
            )
        self.bm_data = None
        self.n_commits = n_commits

    def get_benchmarks(self) -> List[str]:
        return sorted(
            child.stem
            for child in self.benchmark_dir.iterdir()
            if child.is_file() and child.suffix == ".py"
        )

    def print(self):
        if self.bm_data is None:
            print("No benchmark data collected yet!")
            return

        rprint(self.bm_data)

    def plots(self, path: str = ""):
        if path == "":
            location = self.benchmark_dir
        else:
            location = Path(path).resolve()
        location.mkdir(parents=True, exist_ok=True)

        for benchmark, df in self.dataframes.items():
            df.plot()
            plt.title(f"Benchmark: {benchmark}")
            plt.xticks(rotation=45, ha="right")
            plt.legend()
            plt.savefig(location / f"{benchmark}.png", bbox_inches="tight")

    @property
    def commits(self) -> List[Commit]:
        return list(self.repo.iter_commits(max_count=self.n_commits, first_parent=True))

    @property
    def dataframes(self) -> Dict[str, pd.DataFrame]:
        if self.bm_data is None:
            raise RuntimeWarning("No benchmark data collected yet!")

        dfs = dict()
        for benchmark, data in self.bm_data.items():
            # Use fixed columns to generate NaN for missing commits
            df = pd.DataFrame(data, columns=self.commits)
            # Since we want series over commits, use those as index
            df = df.T
            # Reverse commits, so first one is the oldest, last one is the latest
            df = df[::-1]

            def get_short_msg(commit):
                return commit.message.splitlines(keepends=False)[0]

            def get_short_sha(commit):
                return commit.hexsha[:7]

            df.index = df.index.map(
                lambda commit: (f"{get_short_msg(commit)} ({get_short_sha(commit)})")
            )
            dfs[benchmark] = df
        return dfs

    def run(self, verbosity=0, clear_cache=False, benchmarks=None, install=False):
        def debug(*args, **kwargs):
            if verbosity > 0:
                print(*args, **kwargs)

        repo_name = self.path.name
        print(f"Benchmarking repository '{repo_name}'")

        available_benchmarks = self.get_benchmarks()
        if not available_benchmarks:
            print("No benchmarks found!")
            return

        if benchmarks is not None:
            for b in benchmarks.copy():
                if b not in available_benchmarks:
                    print(f"Requested benchmark '{b}' was not found! Skipping!")
                    benchmarks.remove(b)
        else:
            benchmarks = available_benchmarks

        if not benchmarks:
            print("No valid benchmarks selected! Available benchmarks:")
            for b in available_benchmarks:
                print(f"- {b}")
            return
        print("Selected benchmarks:")
        for b in benchmarks:
            print(f"- {b}")

        skipped_benchmarks = [b for b in available_benchmarks if b not in benchmarks]
        if skipped_benchmarks:
            debug("Skipped benchmarks:")
            for b in skipped_benchmarks:
                debug(f"- {b}")

        for commit in self.commits:

            short_msg = commit.message.splitlines(keepends=False)[0]
            print(f"\nBenchmarking commit '{short_msg}' ({commit.hexsha})")

            caches = {
                benchmark: self.data_dir / f"{commit.hexsha}_{benchmark}.pickle"
                for benchmark in benchmarks
            }

            existing_caches = set(cache for cache in caches.values() if cache.exists())
            if existing_caches and clear_cache:
                print(f"Overwriting caches...")
                for cache in existing_caches:
                    cache.unlink()
                existing_caches = set()

            if existing_caches == set(caches.values()):
                print(f"Skipping cached benchmark!")
                continue

            with TemporaryDirectory() as tmp:
                tmp_folder = Path(tmp).resolve()

                debug(f"Creating snapshot in {tmp_folder}")

                self.repo.git.worktree(
                    "add", "--detach", str(tmp_folder), commit.hexsha
                )

                if install:

                    debug(f"Creating virtual environment for benchmarking")
                    venv_dir = tmp_folder / ".venv"
                    virtualenv.cli_run([str(venv_dir)])

                    activate_file = str(venv_dir / "bin" / "activate")

                    def install(name, *libs):
                        debug(f"Installing {name}...", end="")
                        # NOTE: we want to run pip of the venv, so we need to make sure that the
                        # environment for the venv is loaded before. This can only reliably happen
                        # with the activiation script. Note that the 'source' command is not
                        # available in 'sh', but only in 'bash', so we need to select this shell
                        # explicitly!
                        proc = subprocess.run(
                            f"source {activate_file} && python -m pip install -U {' '.join(libs)}",
                            shell=True,
                            executable="bash",  # for 'source' to work
                            capture_output=True,
                            encoding="utf-8",
                        )
                        if proc.stderr:
                            print(f"Error installing {name}:")
                            for l in proc.stderr.splitlines():
                                print(f"|  {l}")
                        else:
                            debug(f"DONE!")
                            for l in proc.stdout.splitlines():
                                debug(f"|  {l}")

                    install("Repository", str(tmp_folder))
                    # TODO: these have to be dynamic somehow!
                    install("Dependencies", "pupil-detectors", "opencv-python")

                    print(f"Collecting benchmark data:")
                    for benchmark in benchmarks:
                        path = self.benchmark_dir / f"{benchmark}.py"
                        print(f"Running benchmark '{benchmark}'...")
                        # NOTE: Running this as non-shell allows to hook the Python debugger into this!
                        # While we want to run this in the venv, this does not work properly when
                        # starting a non-shell subprocess. Instead, 'collector.py' activates the
                        # environment itself internally. For this to work properly, we can NOT use the
                        # venv python binary to run collector.py!
                        with subprocess.Popen(
                            [
                                sys.executable,
                                "-u",  # unbuffered stdout/stderr for realtime benchmark output
                                str(Path(collector.__file__).resolve()),
                                str(path),
                                commit.hexsha,
                                str(self.data_dir),
                                str(venv_dir),
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            encoding="utf-8",
                            cwd=str(self.benchmark_dir),
                        ) as process:
                            for line in iter(process.stdout.readline, ""):
                                print(f"|  {line}", end="")
                else:
                    debug(f"Replacing benchmark folder in snapshot")

                    snapshot_benchmark_folder = tmp_folder / "benchmarks"
                    if snapshot_benchmark_folder.exists():
                        shutil.rmtree(snapshot_benchmark_folder, ignore_errors=True)
                    shutil.copytree(self.benchmark_dir, snapshot_benchmark_folder)

                    print(f"Collecting benchmark data:")
                    for benchmark in benchmarks:
                        path = snapshot_benchmark_folder / f"{benchmark}.py"
                        print(f"Running benchmark '{benchmark}'...")
                        with subprocess.Popen(
                            [
                                sys.executable,
                                "-u",  # unbuffered stdout/stderr for realtime benchmark output
                                str(Path(collector.__file__).resolve()),
                                str(path),
                                commit.hexsha,
                                str(self.data_dir),
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            encoding="utf-8",
                            cwd=str(snapshot_benchmark_folder),
                        ) as process:
                            for line in iter(process.stdout.readline, ""):
                                print(f"|  {line}", end="")

                # create dummy dump if benchmark failed in order to not re-run this every time!
                for cache in caches.values():
                    if not cache.exists():
                        print(
                            f"No cache found, benchmark probably failed!"
                            f" Creating failure cache!"
                        )
                        with cache.open("wb") as f:
                            pickle.dump(None, f)

            self.repo.git.worktree("prune")
            print(f"Done benchmarking commit '{commit.hexsha}'!")

        print()
        print(f"Collected all benchmark data.")

        # collect all snapshot data in single data structure
        self.bm_data = dict()
        for benchmark in benchmarks:
            commit_data = dict()
            for commit in self.commits:
                cache = self.data_dir / f"{commit.hexsha}_{benchmark}.pickle"

                if not cache.exists():
                    print(
                        f"Could not find data for benchmark '{benchmark}'"
                        f" for commit '{commit.hexsha}'!"
                    )
                    continue
                with cache.open("rb") as f:
                    commit_data[commit] = pickle.load(f)
            self.bm_data[benchmark] = commit_data
