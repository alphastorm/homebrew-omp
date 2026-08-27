#!/usr/bin/env python3
"""Convert the distribution lane's exact OMP cask into the OMP NInfer beta channel."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPLACEMENTS = {
    'cask "omp" do': 'cask "omp-beta" do',
    '  name "Oh My Pi"': '  name "OMP NInfer Beta"',
    '  desc "Downstream Oh My Pi coding harness with native Code Mode"': (
        '  desc "Oh My Pi beta with stateful NInfer Responses integration"'
    ),
    '  homepage "https://github.com/alphastorm/omp-monorepo"': (
        '  homepage "https://github.com/alphastorm/omp-ninfer"'
    ),
}
STABLE_CONFLICT_STANZA = '  conflicts_with cask: "omp-beta"\n'
BETA_CONFLICT_STANZA = '  conflicts_with cask: "omp"\n'


def transform(source: str) -> str:
    rendered = source
    for old, new in REPLACEMENTS.items():
        count = rendered.count(old)
        if count != 1:
            raise ValueError(f"expected exactly one {old!r}, found {count}")
        rendered = rendered.replace(old, new)

    if rendered.count(STABLE_CONFLICT_STANZA) != 1:
        raise ValueError("expected exactly one stable-channel conflict")
    if rendered.count("conflicts_with") != 1:
        raise ValueError("input cask contains an unrelated conflict stanza")
    rendered = rendered.replace(STABLE_CONFLICT_STANZA, BETA_CONFLICT_STANZA)

    if 'cask "omp" do' in rendered:
        raise ValueError("stable cask token survived beta rendering")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        rendered = transform(args.input.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"beta cask rendering failed: {error}", file=sys.stderr)
        return 1

    if args.check:
        try:
            existing = args.output.read_text(encoding="utf-8")
        except OSError as error:
            print(f"beta cask check failed: {error}", file=sys.stderr)
            return 1
        if existing != rendered:
            print("beta cask check failed: output differs from deterministic rendering", file=sys.stderr)
            return 1
        print(f"verified {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
