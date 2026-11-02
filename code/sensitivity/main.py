"""Sensitivity-analysis entry point.

Run:
    python code/sensitivity/main.py --seed 42 [--data <dir>]

Conventions:
  * figures (PDF) -> figures/sensitivity/*.pdf
  * numbers that appear in PART sens of paper_content.tex must come from here
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
        return {"x": [1, 2, 3], "y": [2.5, 4.5, 6.5]}
    raise NotImplementedError(f"load the files in {data_dir} here")


def solve(data, seed: int) -> dict:
    """Return the sensitivity results (one factor at a time, ranges)."""
    return {"seed": seed, "factors": {}, "note": "replace with your analysis"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sensitivity analysis")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data", type=pathlib.Path, default=None)
    args = parser.parse_args()

    result = solve(load_data(args.data), args.seed)
    out = ROOT / "code" / "results" / "sensitivity_metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
