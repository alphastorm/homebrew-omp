#!/usr/bin/env python3
"""Verify the OMP cask is bound to the uploaded GitHub release asset."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY = "alphastorm/homebrew-omp"
CASK = Path(__file__).resolve().parents[1] / "Casks" / "omp.rb"
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
    source = CASK.read_text(encoding="utf-8")
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

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        fail("GITHUB_TOKEN is required to inspect the private release asset")

    api_url = f"https://api.github.com/repos/{REPOSITORY}/releases/assets/{asset_id}"
    request = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "homebrew-omp-cask-verifier",
        },
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
