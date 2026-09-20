import json
from pathlib import Path
import unittest

from axm_avatar_machine.blueprint import compile_blueprint
from axm_avatar_machine.material_response import (
    MaterialResponseHold,
    active_organs,
    material_response_catalog,
    resolve_material_response,
)

ROOT = Path(__file__).resolve().parents[1]


class MaterialResponseTests(unittest.TestCase):
    def test_catalog_has_13_families_and_8_organs(self):
        self.assertEqual(material_response_catalog()["counts"], {"families": 13, "organs": 8})

    def test_skin_living_is_preserved_as_unbound_behavior(self):
        value = resolve_material_response("skin-living", color_hex="#d3a27f")
        self.assertEqual(set(value["active_organs"]), {"surface.subsurface", "surface.sheen", "surface.coat", "surface.breakup"})
        self.assertEqual(value["renderer_binding"], "HOLD_BLUEPRINT_BLENDER_ORGANS_NOT_BOUND")

    def test_zero_weights_are_true_noop(self):
        response = {
            "roughness": 0.5,
            "subsurface": {"weight": 0},
            "sheen": {"weight": 0},
            "anisotropy": {"strength": 0},
            "clearcoat": {"weight": 0},
            "breakup": {"roughness_variation": 0, "color_variation": 0, "scale_mm": 2},
            "transmission": 0,
            "iridescence": {"weight": 0},
            "layers": [],
        }
        self.assertEqual(active_organs(response), [])

    def test_unknown_family_fails_closed(self):
        with self.assertRaises(MaterialResponseHold):
            resolve_material_response("not-real")

    def test_surface_response_changes_appearance_not_geometry(self):
        base = json.loads((ROOT / "examples" / "blueprint-doll-pair-v1.json").read_text())
        changed = json.loads((ROOT / "examples" / "blueprint-doll-pair-material-response-v1.json").read_text())
        a, b = compile_blueprint(base), compile_blueprint(changed)
        self.assertEqual(a["geometry_signature"], b["geometry_signature"])
        self.assertEqual(a["behavior_signature"], b["behavior_signature"])
        self.assertNotEqual(a["appearance_signature"], b["appearance_signature"])
        selected = [m for m in b["materials"] if m.get("response_family")]
        self.assertTrue(selected)
        self.assertTrue(all(m["response_renderer_binding"].startswith("HOLD_") for m in selected))


if __name__ == "__main__":
    unittest.main()
