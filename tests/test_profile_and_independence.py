import json
from pathlib import Path
import unittest

from axm_avatar_machine.paths import machine_root
from axm_avatar_machine.pipeline import ReferenceInterpretationHold, load_request
from axm_avatar_machine.profile import PROFILE_ID, load_profile


class ProfileTests(unittest.TestCase):
    def test_profile_exposes_one_common_pipeline(self):
        profile = load_profile()
        self.assertEqual(profile["id"], PROFILE_ID)
        self.assertTrue(profile["common_pipeline"])
        self.assertEqual(set(profile["output_modes"]), {"visual", "clip", "3d", "animated-3d"})
        self.assertEqual(profile["reference_interpretation"]["status"], "HOLD_PLATFORM_MODEL_ASSISTED")

    def test_example_request_loads(self):
        request = load_request(machine_root() / "examples" / "odd-shift-duo.json")
        self.assertEqual(request["profile"], PROFILE_ID)

    def test_profile_retains_creator_parts_as_source_authority(self):
        root = machine_root()
        path = root / "profiles" / "doll" / "odd-shift-duo" / "creator-parts.json"
        parts = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(parts["source_authority"])
        self.assertTrue(parts["realizations_are_secondary"])
        self.assertIn("growth_rule", parts["deduplication"])
        self.assertIn("construction-source", parts["retained_layers"])
        self.assertIn("motion-keyframes", parts["retained_layers"])
        self.assertGreaterEqual(len(parts["construction_primitives"]), 7)

    def test_arbitrary_reference_fails_honestly(self):
        root = machine_root()
        path = root / "tests" / "_reference_hold_request.json"
        try:
            path.write_text(json.dumps({
                "profile": PROFILE_ID,
                "modes": ["visual"],
                "reference_images": ["person.jpg"],
            }), encoding="utf-8")
            with self.assertRaises(ReferenceInterpretationHold):
                load_request(path)
        finally:
            path.unlink(missing_ok=True)

    def test_runtime_code_has_no_uc_import_or_path(self):
        root = machine_root()
        checked = list((root / "src").rglob("*.py")) + list((root / "blender").glob("*.py"))
        for path in checked:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("import axm_uc", text, path)
            self.assertNotIn("from axm_uc", text, path)
            self.assertNotIn("axm-universal-creation", text, path)
            self.assertNotIn("/opt/codex", text, path)
            self.assertNotIn("/usr/lib/python", text, path)


if __name__ == "__main__":
    unittest.main()
