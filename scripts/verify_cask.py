#!/usr/bin/env python3
"""Verify an OMP channel cask is bound to the uploaded GitHub release asset."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY = "alphastorm/homebrew-omp"
DEFAULT_CASK = Path(__file__).resolve().parents[1] / "Casks" / "omp.rb"
VERSION_PATTERN = r"[0-9]+\.[0-9]+\.[0-9]+-[a-f0-9]{7,40}"
SHA256_PATTERN = r"[a-f0-9]{64}"


def fail(message: str) -> None:
    print(f"cask verification failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def one_match(pattern: str, source: str, label: str) -> str:
    matches = re.findall(pattern, source, flags=re.MULTILINE)
    if len(matches) != 1:
        fail(f"expected exactly one {label}, found {len(matches)}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cask", type=Path, default=DEFAULT_CASK)
    parser.add_argument("--token", choices=("omp", "omp-beta"), default="omp")
    args = parser.parse_args()

    source = args.cask.read_text(encoding="utf-8")
    declared_token = one_match(r'^cask "([^"]+)" do$', source, "cask token")
    if declared_token != args.token:
        fail(f"expected cask token {args.token!r}, found {declared_token!r}")
    conflicting_token = "omp-beta" if args.token == "omp" else "omp"
    one_match(
        rf'^\s*conflicts_with cask: "{conflicting_token}"$',
        source,
        "opposite-channel conflict",
    )
    if args.token == "omp-beta":
        one_match(
            r'^\s*homepage "https://github\.com/alphastorm/omp-ninfer"$',
            source,
            "OMP NInfer homepage",
        )
    version = one_match(
        rf'^\s*version "({VERSION_PATTERN})"$', source, "pinned version"
    )
    sha256 = one_match(
        rf'^\s*sha256 "({SHA256_PATTERN})"$', source, "pinned sha256"
    )
    asset_id = int(
        one_match(
            r'^\s*url "https://api\.github\.com/repos/alphastorm/homebrew-omp/'
            r'releases/assets/([0-9]+)#omp-#\{version\}-darwin-arm64\.tar\.gz",$',
            source,
            "GitHub release asset URL",
        )
    )

    api_url = f"https://api.github.com/repos/{REPOSITORY}/releases/assets/{asset_id}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "homebrew-omp-cask-verifier",
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        api_url,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            asset = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        fail(f"GitHub asset lookup failed: {error}")

    expected_name = f"omp-{version}-darwin-arm64.tar.gz"
    expected_digest = f"sha256:{sha256}"
    expected_download_suffix = f"/releases/download/omp-{version}/{expected_name}"
    checks = {
        "asset id": asset.get("id") == asset_id,
        "asset name": asset.get("name") == expected_name,
        "uploaded state": asset.get("state") == "uploaded",
        "non-empty asset": isinstance(asset.get("size"), int) and asset["size"] > 0,
        "asset digest": asset.get("digest") == expected_digest,
        "release tag": str(asset.get("browser_download_url", "")).endswith(
            expected_download_suffix
        ),
    }
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        fail(", ".join(failed))

    print(f"verified {expected_name} ({asset['size']} bytes, {expected_digest})")


if __name__ == "__main__":
    main()
