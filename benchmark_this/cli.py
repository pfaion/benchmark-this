import argparse
import sys
from pathlib import Path

from .benchmark import Benchmarker


def main():
    parser = argparse.ArgumentParser(description="Run benchmarks on a git repository.")
    parser.add_argument(
        "-r",
        "--repo",
        type=Path,
        default=".",
        action="store",
        help="the repository to benchmark (default: current working directory)",
    )
    parser.add_argument(
        "-n",
        type=int,
        default=10,
        action="store",
        help="number of commits to benchmark (default: 10)",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="enable to list available benchmarks and exit",
    )
    parser.add_argument(
        "-c",
        "--clear-cache",
        action="store_true",
        help="enable to overwrite existing benchmark caches",
    )
    parser.add_argument(
        "-p", "--print", action="store_true", help="enable to print outputs to console"
    )
    parser.add_argument(
        "-i",
        "--images",
        action="store",
        type=str,
        default="",
        help="specify a path to store generic plots for the benchmarks",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        default=0,
        action="count",
        help="enable to print verbose output",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="enable to install the repo in a virtualenv before running the benchmarks",
    )
    parser.add_argument(
        "benchmarks",
        nargs="*",
        action="store",
        help="list of benchmarks to run, omit to run all available benchmarks",
    )
    args = parser.parse_args()
    bench = Benchmarker(path=args.repo, n_commits=args.n)

    if args.list:
        benchmarks = bench.get_benchmarks()
        if not benchmarks:
            print("No benchmarks found.")
            return

        print("Found benchmarks:")
        for name in benchmarks:
            print(f"- {name}")
        return

    bench.run(
        verbosity=args.verbose,
        clear_cache=args.clear_cache,
        benchmarks=args.benchmarks or None,
        install=args.install,
    )

    if args.print:
        bench.print()

    if args.images != "":
        print(f"Saving generated plots to '{Path(args.images).resolve()}'")
        bench.plots(args.images)
