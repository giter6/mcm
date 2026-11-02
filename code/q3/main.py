"""Problem 3 entry point.

Run:
    python code/q3/main.py --seed 42 [--data <dir>]

Conventions:
  * metrics/parameters -> code/results/q3_metrics.json
  * figures (PDF)       -> figures/q3/*.pdf
  * contest data is not committed; pass it with --data
"""
from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_data(data_dir: pathlib.Path | None):
    """Load the contest data (same rules as code/q1/main.py)."""
    if data_dir is None:
        print("[info] --data not given: using a synthetic placeholder.")
        return {"x": [1, 2, 3], "y": [4, 6, 8]}
    raise NotImplementedError(f"load the files in {data_dir} here")


def solve(data, seed: int) -> dict:
    """Return the numbers that are reported in the paper for Problem 3."""
    return {"seed": seed, "rmse": 0.0, "note": "replace with your model"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Problem 3")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data", type=pathlib.Path, default=None)
    args = parser.parse_args()

    result = solve(load_data(args.data), args.seed)
    out = ROOT / "code" / "results" / "q3_metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
