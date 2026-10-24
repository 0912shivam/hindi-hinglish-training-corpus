from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FLAM corpus cleaning pipeline")
    parser.add_argument("raw_dir", type=Path, help="Path to raw input directory")
    parser.add_argument("out_dir", type=Path, help="Path to output directory")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run_pipeline(args.raw_dir, args.out_dir)


if __name__ == "__main__":
    main()
