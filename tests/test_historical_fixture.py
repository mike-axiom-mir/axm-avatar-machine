import unittest

from axm_avatar_machine.glb import inspect_glb, sha256
from axm_avatar_machine.media import png_dimensions, probe_video
from axm_avatar_machine.paths import machine_root


class HistoricalFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = machine_root() / "fixtures" / "odd-shift-duo" / "historical"

    def test_exact_retained_hashes(self):
        expected = {
            "Odd-Shift-Duo.blend": "2b41f7c625924e2beccb40bccdfb7c58f344eb03c1fad76d5614f4cc8f6dc56f",
            "Odd-Shift-Duo.glb": "80ff2fe0049aff5f37053eff1475c4256ae0179cd52d217402eaeeaec8ddcb07",
            "Odd-Shift-Duo-Poster.png": "a816fac2f4a2f468a2a4ff32ec3279f43d4fe25d35b47f5ae5536b57e8c1c2ed",
            "Odd-Shift-Duo-Preview.mp4": "5b9736ee61904250ea913bb9645fb043e9cd3cbbca090b4acdfdaa5648e38c9d",
        }
        for name, digest in expected.items():
            self.assertEqual(sha256(self.fixture / name), digest)

    def test_glb_structure_is_decoded_not_copied_from_claim(self):
        result = inspect_glb(self.fixture / "Odd-Shift-Duo.glb")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["metrics"]["meshes"], 105)
        self.assertEqual(result["metrics"]["materials"], 28)
        self.assertEqual(result["metrics"]["skins"], 1)
        self.assertEqual(result["metrics"]["joints"], 34)
        self.assertEqual(result["metrics"]["skin_bindings"], 0)
        self.assertEqual(result["metrics"]["animation_channels"], 102)
        self.assertEqual(result["animation_names"], ["OddShift_Duo_Demo"])
        self.assertEqual(result["deformation"]["model"], "RIGID_BONE_PARENTING")
        self.assertFalse(result["deformation"]["skinned_mesh_deformation"])

    def test_visible_and_motion_artifacts_are_real_files(self):
        self.assertEqual(png_dimensions(self.fixture / "Odd-Shift-Duo-Poster.png"), (900, 900))
        probe = probe_video(self.fixture / "Odd-Shift-Duo-Preview.mp4")
        self.assertEqual(probe["streams"][0]["codec_name"], "h264")
        self.assertEqual((probe["streams"][0]["width"], probe["streams"][0]["height"]), (640, 640))
        self.assertAlmostEqual(float(probe["format"]["duration"]), 6.0, places=2)


if __name__ == "__main__":
    unittest.main()
