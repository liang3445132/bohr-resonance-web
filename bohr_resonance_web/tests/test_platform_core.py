from pathlib import Path
import unittest

import numpy as np

from platform_core import analyze_damping_upload, analyze_forced_upload


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PlatformCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        damping_path = PROJECT_ROOT / "damping_analysis" / "data" / "阻尼电流原始数据.xlsx"
        forced_path = PROJECT_ROOT / "forced_analysis" / "data" / "受迫振动原始数据.xlsx"
        cls.damping = analyze_damping_upload(damping_path.read_bytes(), damping_path.name)
        cls.forced = analyze_forced_upload(forced_path.read_bytes(), forced_path.name, beta=0.109)

    def test_damping_result(self) -> None:
        self.assertGreater(self.damping.fit.r_squared, 0.99)
        self.assertAlmostEqual(self.damping.beta_at_0300 or 0.0, 0.109, places=8)
        self.assertTrue(self.damping.plot_png.startswith(b"\x89PNG"))
        self.assertEqual(len(self.damping.processed), 10)

    def test_forced_result(self) -> None:
        self.assertAlmostEqual(self.forced.omega0, 3.62, places=8)
        self.assertAlmostEqual(self.forced.amplitude_max, 75.1, places=8)
        peak = self.forced.processed["amplitude_deg"].idxmax()
        self.assertTrue(np.isclose(self.forced.processed.loc[peak, "phase_pi"], -0.5))
        self.assertTrue(self.forced.amplitude_png.startswith(b"\x89PNG"))
        self.assertTrue(self.forced.phase_png.startswith(b"\x89PNG"))
        self.assertEqual(len(self.forced.processed), 15)


if __name__ == "__main__":
    unittest.main()
