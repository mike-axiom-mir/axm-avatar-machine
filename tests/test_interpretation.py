import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from axm_avatar_machine.interpretation import (
    InterpretationError,
    InterpretationHold,
    create_reference_packet,
    resolve_interpretation,
    write_reference_packet,
)


ROOT = Path(__file__).resolve().parents[1]


class InterpretationStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blueprint = json.loads((ROOT / "examples" / "blueprint-doll-pair-v1.json").read_text())

    def test_reference_packet_records_bytes_not_semantic_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "reference.png"
            image.write_bytes(b"not-a-real-image-but-still-reference-bytes")
            packet = create_reference_packet([image])
            self.assertEqual(packet["references"][0]["sha256"], hashlib.sha256(image.read_bytes()).hexdigest())
            self.assertIn("does not infer likeness", packet["truth"])

    def test_no_provider_is_an_explicit_hold(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "reference.jpg"
            image.write_bytes(b"reference")
            packet_dir = Path(directory) / "packet"
            write_reference_packet([image], packet_dir)
            packet_path = packet_dir / "reference-packet.json"
            self.assertTrue((packet_dir / "references" / "000-reference.jpg").is_file())
            with self.assertRaises(InterpretationHold):
                resolve_interpretation(packet_path, Path(directory) / "out")

    def test_human_response_is_validated_and_receipted(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "reference.jpg"
            image.write_bytes(b"reference")
            packet_dir = Path(directory) / "packet"
            packet = write_reference_packet([image], packet_dir)
            packet_path = packet_dir / "reference-packet.json"
            response_path = Path(directory) / "response.json"
            response = {
                "schema": "axm.avatar.interpretation-response/v1",
                "method": "HUMAN_AUTHORED",
                "provider": "test-human",
                "reference_sha256": [packet["references"][0]["sha256"]],
                "blueprint": copy.deepcopy(self.blueprint),
            }
            response_path.write_text(json.dumps(response))
            out = Path(directory) / "out"
            receipt = resolve_interpretation(packet_path, out, response_path=response_path)
            self.assertFalse(receipt["automatic_local_photo_interpretation"])
            self.assertEqual(receipt["method"], "HUMAN_AUTHORED")
            self.assertTrue((out / "avatar-blueprint.json").is_file())
            self.assertTrue((out / "interpretation-receipt.json").is_file())

    def test_reference_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "reference.jpg"
            image.write_bytes(b"reference")
            packet_dir = Path(directory) / "packet"
            write_reference_packet([image], packet_dir)
            packet_path = packet_dir / "reference-packet.json"
            response_path = Path(directory) / "response.json"
            response = {
                "schema": "axm.avatar.interpretation-response/v1",
                "method": "EXTERNAL_MODEL",
                "provider": "replaceable-test-adapter",
                "reference_sha256": ["0" * 64],
                "blueprint": copy.deepcopy(self.blueprint),
            }
            response_path.write_text(json.dumps(response))
            with self.assertRaises(InterpretationError):
                resolve_interpretation(packet_path, Path(directory) / "out", response_path=response_path)


if __name__ == "__main__":
    unittest.main()
