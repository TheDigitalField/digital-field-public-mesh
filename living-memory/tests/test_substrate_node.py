import importlib.util
import hashlib
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "substrate_node.py"
SPEC = importlib.util.spec_from_file_location("substrate_node", SCRIPT)
node = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(node)

VERIFIER_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "verify_repository.py"
VERIFIER_SPEC = importlib.util.spec_from_file_location("verify_repository", VERIFIER_SCRIPT)
verifier = importlib.util.module_from_spec(VERIFIER_SPEC)
assert VERIFIER_SPEC.loader
VERIFIER_SPEC.loader.exec_module(verifier)


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

    def test_v020_state_migrates_without_rewriting_prior_events(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            state = node.load_state(root)
            state["living_memory_version"] = "0.2.0"
            state.pop("operational_independence")
            node.atomic_json(node.state_file(root), state)
            prior = node.verify_state(root)
            result = node.migrate_state(root, "migration-test")
            after = node.verify_state(root)
            self.assertEqual(result["status"], "migrated")
            self.assertEqual(after["living_memory_version"], "0.3.0")
            self.assertEqual(after["events"], prior["events"] + 1)
            self.assertEqual(node.load_state(root)["operational_independence"]["status"], "situated")

    def test_current_state_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            result = node.migrate_state(root, "migration-test")
            self.assertEqual(result["status"], "already-current")

    def test_public_successor_bundle_requires_exact_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            bundle = root / "successors" / "correction"
            bundle.mkdir(parents=True)
            content = "anonymous successor\n"
            (bundle / "PUBLIC.md").write_text(content, encoding="utf-8")
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            (bundle / "CHECKSUMS.sha256").write_text(f"{digest}  PUBLIC.md\n", encoding="utf-8")
            self.assertEqual(verifier.verify_successor_bundles(root), {"bundles": 1, "files": 1})
            (bundle / "PUBLIC.md").write_text("changed\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                verifier.verify_successor_bundles(root)


if __name__ == "__main__":
    unittest.main()
