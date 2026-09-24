import copy
import json
from pathlib import Path
import unittest

from axm_avatar_machine.blueprint import BlueprintError, compile_blueprint, validate_blueprint


ROOT = Path(__file__).resolve().parents[1]


class BlueprintCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blueprint = json.loads((ROOT / "examples" / "blueprint-doll-pair-v1.json").read_text())

    def test_compiles_deterministically(self):
        first = compile_blueprint(self.blueprint)
        second = compile_blueprint(copy.deepcopy(self.blueprint))
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "axm.avatar.scene-plan/v1")
        self.assertEqual(len(first["bones"]), 34)
        self.assertGreater(len(first["objects"]), 30)
        self.assertGreater(len(first["animation"]), 10)
        self.assertEqual(first["truth_boundary"]["deformation"], "RIGID_BONE_PARENTING")

    def test_color_change_does_not_change_geometry_signature(self):
        changed = copy.deepcopy(self.blueprint)
        changed["characters"][0]["palette"]["primary"] = "#ff00aa"
        a = compile_blueprint(self.blueprint)
        b = compile_blueprint(changed)
        self.assertEqual(a["geometry_signature"], b["geometry_signature"])
        self.assertNotEqual(a["appearance_signature"], b["appearance_signature"])
        self.assertNotEqual(a["plan_sha256"], b["plan_sha256"])

    def test_real_geometry_control_changes_geometry_signature(self):
        changed = copy.deepcopy(self.blueprint)
        changed["characters"][0]["proportions"]["head"] = 1.2
        self.assertNotEqual(
            compile_blueprint(self.blueprint)["geometry_signature"],
            compile_blueprint(changed)["geometry_signature"],
        )

    def test_animation_change_changes_behavior_not_geometry(self):
        changed = copy.deepcopy(self.blueprint)
        changed["animation_beats"][1]["frame"] = 41
        a = compile_blueprint(self.blueprint)
        b = compile_blueprint(changed)
        self.assertEqual(a["geometry_signature"], b["geometry_signature"])
        self.assertNotEqual(a["behavior_signature"], b["behavior_signature"])

    def test_optional_anatomy_defaults_preserve_old_style_without_detail_objects(self):
        plan = compile_blueprint(self.blueprint)
        ids = {item["id"] for item in plan["objects"]}
        self.assertNotIn("compact:nose", ids)
        self.assertNotIn("compact:jaw", ids)
        self.assertNotIn("compact:L-ear", ids)

    def test_anatomy_controls_change_geometry_not_behavior(self):
        changed = copy.deepcopy(self.blueprint)
        changed["characters"][0]["anatomy"] = {
            "head_width": 1.18,
            "head_depth": 0.92,
            "eye_spacing": 0.85,
            "eye_size": 0.82,
            "nose_size": 0.7,
            "nose_projection": 1.15,
            "ear_size": 0.65,
            "jaw_width": 1.05,
            "mouth_width": 1.1,
            "shoulder_width": 1.16,
            "hip_width": 1.08,
            "limb_thickness": 1.12,
            "hand_size": 1.08,
            "foot_size": 1.05,
        }
        a = compile_blueprint(self.blueprint)
        b = compile_blueprint(changed)
        self.assertNotEqual(a["geometry_signature"], b["geometry_signature"])
        self.assertEqual(a["behavior_signature"], b["behavior_signature"])
        ids = {item["id"] for item in b["objects"]}
        for expected in ("compact:nose", "compact:jaw", "compact:L-ear", "compact:R-ear"):
            self.assertIn(expected, ids)

    def test_unknown_anatomy_control_fails_closed(self):
        changed = copy.deepcopy(self.blueprint)
        changed["characters"][0]["anatomy"] = {"magic_face_slider": 1.0}
        with self.assertRaises(BlueprintError):
            validate_blueprint(changed)


    def test_future_profile_family_is_not_silently_accepted(self):
        changed = copy.deepcopy(self.blueprint)
        changed["style"]["family"] = "realistic-avatar"
        with self.assertRaises(BlueprintError):
            validate_blueprint(changed)

    def test_invalid_palette_fails(self):
        changed = copy.deepcopy(self.blueprint)
        changed["characters"][0]["palette"]["skin"] = "beige"
        with self.assertRaises(BlueprintError):
            validate_blueprint(changed)


if __name__ == "__main__":
    unittest.main()
