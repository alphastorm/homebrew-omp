from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_beta_cask", ROOT / "scripts" / "render_beta_cask.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
transform = MODULE.transform


SOURCE = (
    ROOT / "release-sources" / "omp-18.0.9-cross-platform-beta-1.rb"
).read_text(encoding="utf-8")


class RenderBetaCaskTest(unittest.TestCase):
    def test_rebrands_channel_without_changing_pins(self) -> None:
        rendered = transform(SOURCE)

        self.assertIn('cask "omp-beta" do', rendered)
        self.assertIn('name "OMP NInfer Beta"', rendered)
        self.assertIn('homepage "https://github.com/alphastorm/omp-ninfer"', rendered)
        self.assertIn('conflicts_with cask: "omp"', rendered)
        for prefix in ("  version ", "  sha256 ", "  url "):
            source_line = next(
                line for line in SOURCE.splitlines() if line.startswith(prefix)
            )
            self.assertIn(source_line, rendered)
        self.assertIn('args:         ["--activate"]', rendered)
        self.assertIn('args:         ["--uninstall"]', rendered)
        self.assertNotIn('cask "omp" do', rendered)

    def test_rejects_drifted_distribution_template(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected exactly one"):
            transform(SOURCE.replace('name "Oh My Pi"', 'name "Renamed"'))

    def test_rejects_unrelated_conflict_input(self) -> None:
        source = SOURCE.replace(
            '  conflicts_with cask: "omp-beta"\n',
            '  conflicts_with cask: "other"\n',
        )
        with self.assertRaisesRegex(ValueError, "stable-channel conflict"):
            transform(source)


if __name__ == "__main__":
    unittest.main()
