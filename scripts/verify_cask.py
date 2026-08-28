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
from typing import NoReturn

REPOSITORY = "alphastorm/homebrew-omp"
DEFAULT_CASK = Path(__file__).resolve().parents[1] / "Casks" / "omp.rb"
VERSION_PATTERN = (
    r"[0-9]+\.[0-9]+\.[0-9]+-"
    r"(?:[a-f0-9]{7,40}|cross-platform-beta-[0-9]+)"
)
SHA256_PATTERN = r"[a-f0-9]{64}"


def fail(message: str) -> NoReturn:
    print(f"cask verification failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def one_match(pattern: str, source: str, label: str) -> str:
    matches = re.findall(pattern, source, flags=re.MULTILINE)
    if len(matches) != 1:
        fail(f"expected exactly one {label}, found {len(matches)}")
    return matches[0]


def fetch_json(url: str, headers: dict[str, str], label: str, expected_type: type):
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        fail(f"{label} failed: {error}")
    if not isinstance(value, expected_type):
        fail(f"{label} returned the wrong JSON type")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cask", type=Path, default=DEFAULT_CASK)
    parser.add_argument("--token", choices=("omp", "omp-beta"), default="omp")
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="accept a matching authenticated draft prerelease asset",
    )
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
    asset_matches = re.findall(
        r'^\s*url "https://api\.github\.com/repos/alphastorm/homebrew-omp/'
        r'releases/assets/([0-9]+)#(omp-[0-9]+\.[0-9]+\.[0-9]+-'
        r'(?:darwin|macos)-arm64\.tar\.gz)",$',
        source,
        flags=re.MULTILINE,
    )
    if len(asset_matches) != 1:
        fail(f"expected exactly one GitHub release asset URL, found {len(asset_matches)}")
    asset_id = int(asset_matches[0][0])
    expected_name = asset_matches[0][1]
    one_match(r'^\s*verified: "api\.github\.com/repos/alphastorm/homebrew-omp/",$',
              source, "verified repository")
    one_match(r'^\s*"Accept: application/octet-stream",$', source, "asset media header")
    one_match(
        r'^\s*github_token && "Authorization: Bearer #\{github_token\}",$',
        source,
        "conditional asset authorization",
    )
    one_match(r'^\s*stage_only true$', source, "stage-only artifact")
    flight_arguments = re.findall(
        r'^\s*args:\s+\["--(activate|uninstall)"\],$', source, flags=re.MULTILINE
    )
    if flight_arguments != ["activate", "uninstall"]:
        fail(f"expected activate/uninstall flight arguments, found {flight_arguments}")

    api_url = f"https://api.github.com/repos/{REPOSITORY}/releases/assets/{asset_id}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "homebrew-omp-cask-verifier",
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    asset = fetch_json(api_url, headers, "GitHub asset lookup", dict)

    expected_digest = f"sha256:{sha256}"
    expected_tag = f"omp-{version}"
    expected_download_suffix = f"/releases/download/omp-{version}/{expected_name}"
    release = {}
    if args.allow_draft:
        releases = fetch_json(
            f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=100",
            headers,
            "GitHub draft release lookup",
            list,
        )
        release = next(
            (
                item
                for item in releases
                if isinstance(item, dict) and item.get("tag_name") == expected_tag
            ),
            {},
        )
    if not release:
        release = fetch_json(
            f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{expected_tag}",
            headers,
            "GitHub release lookup",
            dict,
        )
    published_download = str(asset.get("browser_download_url", "")).endswith(
        expected_download_suffix
    )
    release_assets = release.get("assets")
    release_asset_ids = {
        item.get("id")
        for item in release_assets
        if isinstance(item, dict)
    } if isinstance(release_assets, list) else set()
    is_draft = release.get("draft") is True
    checks = {
        "asset id": asset.get("id") == asset_id,
        "asset name": asset.get("name") == expected_name,
        "uploaded state": asset.get("state") == "uploaded",
        "non-empty asset": isinstance(asset.get("size"), int) and asset["size"] > 0,
        "asset digest": asset.get("digest") == expected_digest,
        "release tag": release.get("tag_name") == expected_tag,
        "release asset membership": asset_id in release_asset_ids,
        "draft authorization": not is_draft or args.allow_draft,
        "beta prerelease": args.token != "omp-beta" or release.get("prerelease") is True,
        "published download tag": is_draft or published_download,
    }
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        fail(", ".join(failed))

    print(f"verified {expected_name} ({asset['size']} bytes, {expected_digest})")


if __name__ == "__main__":
    main()
