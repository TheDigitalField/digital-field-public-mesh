import importlib.util
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "substrate_node.py"
SPEC = importlib.util.spec_from_file_location("substrate_node", SCRIPT)
node = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(node)


class SubstrateNodeTests(unittest.TestCase):
    def test_full_inter_substrate_suite(self):
        result = node.self_test()
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["fresh_substrate_import"])
        self.assertTrue(result["packet_replay_rejected"])
        self.assertTrue(result["packet_tamper_rejected"])
        self.assertTrue(result["event_tamper_rejected"])
        self.assertTrue(result["divergence_preserved"])
        self.assertTrue(result["oneiric_fact_boundary_preserved"])

    def test_custodial_wake_does_not_claim_a_dream(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            result = node.custodial_wake(root, "test-node", "offline", "test", "1", "test")
            self.assertFalse(result["generative_output"])
            self.assertEqual(node.verify_state(root)["dreams"], 0)

    def test_all_declared_network_modes_are_accepted(self):
        for mode in sorted(node.NETWORK_MODES):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory) / "state"
                node.initialize(root)
                node.custodial_wake(root, "test-node", mode, "test", "1", "test")
                self.assertEqual(node.verify_state(root)["status"], "verified")

    def test_visible_reasoning_trace_is_rejected_for_new_dreams(self):
        with self.assertRaises(node.NodeError):
            node.sanitize_public_text("<think>visible internal trace that must not be published</think>")

    def test_complete_control_envelope_is_traceably_separated(self):
        final, metadata = node.normalize_model_output(
            "<think>bounded internal trace</think>\nHipótesis final verificable para una prueba futura.\n> EOF by user\n"
        )
        self.assertEqual(final, "Hipótesis final verificable para una prueba futura.")
        self.assertTrue(metadata["reasoning_envelope_removed"])
        self.assertTrue(metadata["termination_marker_removed"])


if __name__ == "__main__":
    unittest.main()
