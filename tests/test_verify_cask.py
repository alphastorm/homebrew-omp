from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_cask", ROOT / "scripts" / "verify_cask.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifyCaskArchiveTest(unittest.TestCase):
    def test_beta_cask_uses_the_hosted_installer_contract(self) -> None:
        source = (ROOT / "Casks" / "omp-beta.rb").read_text(encoding="utf-8")
        self.assertEqual(
            MODULE.installer_contract(source),
            ("hosted", "18.0.9-hosted-macos-arm64-f4dcba581e4a"),
        )

    def test_hosted_archive_binds_release_and_binary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "client.tar.gz"
            self._write_archive(archive)
            MODULE.verify_archive(
                archive, "hosted", "18.0.9-hosted-macos-arm64-f4dcba581e4a"
            )

    def test_hosted_archive_rejects_a_missing_installer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "client.tar.gz"
            self._write_archive(archive, include_installer=False)
            with self.assertRaisesRegex(ValueError, "install.sh"):
                MODULE.verify_archive(
                    archive, "hosted", "18.0.9-hosted-macos-arm64-f4dcba581e4a"
                )

    def test_legacy_archive_accepts_its_top_level_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "legacy.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                for name, content in {
                    "install-release": b"installer",
                    "release/release.json": b"{}",
                }.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))
            MODULE.verify_archive(archive_path, "legacy", None)

    @staticmethod
    def _write_archive(path: Path, *, include_installer: bool = True) -> None:
        release_id = "18.0.9-hosted-macos-arm64-f4dcba581e4a"
        binary = b"exact-binary"
        binary_sha256 = hashlib.sha256(binary).hexdigest()
        files = {
            "client-release.json": json.dumps(
                {
                    "releaseId": release_id,
                    "binary": {"name": "omp", "sha256": binary_sha256},
                }
            ).encode(),
            "omp": binary,
            "omp-launcher": b"launcher",
        }
        if include_installer:
            files["install.sh"] = (
                f"release={release_id}\nsha={binary_sha256}\n"
            ).encode()
        with tarfile.open(path, "w:gz") as archive:
            for name, content in files.items():
                info = tarfile.TarInfo(f"omp-18.0.9-macos-arm64/{name}")
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))


if __name__ == "__main__":
    unittest.main()
