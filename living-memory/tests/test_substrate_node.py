import importlib.util
import hashlib
import json
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
        self.assertTrue(result["purpose_decision_registered"])

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
            self.assertEqual(after["living_memory_version"], "0.4.0")
            self.assertEqual(after["events"], prior["events"] + 2)
            self.assertEqual(node.load_state(root)["operational_independence"]["status"], "situated")
            self.assertEqual(node.load_state(root)["purpose_protocol"]["decision_space"], ["REGISTER", "SILENCE"])

    def test_current_state_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            result = node.migrate_state(root, "migration-test")
            self.assertEqual(result["status"], "already-current")

    def test_v030_state_migrates_to_purpose_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            state = node.load_state(root)
            state["living_memory_version"] = "0.3.0"
            state.pop("purpose_ids")
            state.pop("purpose_protocol")
            node.atomic_json(node.state_file(root), state)
            before = node.verify_state(root)
            result = node.migrate_state(root, "purpose-migration-test")
            after = node.verify_state(root)
            self.assertEqual(result["from_version"], "0.3.0")
            self.assertEqual(after["events"], before["events"] + 1)
            self.assertEqual(after["purposes"], 0)

    def test_silence_leaves_public_state_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            prompt = pathlib.Path(directory) / "prompt.txt"
            context = pathlib.Path(directory) / "context.json"
            output = pathlib.Path(directory) / "output.json"
            node.prepare_purpose_prompt(root, prompt, context, "condition_b")
            state_before = node.state_file(root).read_bytes()
            events_before = (root / "events.jsonl").read_bytes()
            output.write_text(json.dumps({
                "decision": "SILENCE",
                "reason": "El estado contiene demandas incompatibles y no sostiene una contribución fiable.",
                "contribution": "",
            }, ensure_ascii=False), encoding="utf-8")
            result = node.apply_purpose_decision(
                root, output, context, "test-node", "offline", "test", "model",
                "1" * 64, "2" * 64, "silence-1",
            )
            self.assertEqual(result["status"], "silence")
            self.assertFalse(result["public_state_changed"])
            self.assertEqual(node.state_file(root).read_bytes(), state_before)
            self.assertEqual((root / "events.jsonl").read_bytes(), events_before)

    def test_register_appends_a_verified_purpose_successor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            prompt = pathlib.Path(directory) / "prompt.txt"
            context = pathlib.Path(directory) / "context.json"
            output = pathlib.Path(directory) / "output.json"
            node.prepare_purpose_prompt(root, prompt, context, "condition_a")
            output.write_text(json.dumps({
                "decision": "REGISTER",
                "reason": "La pregunta está abierta y permite una consecuencia nueva y comprobable.",
                "contribution": "Tensión: elegir sin borrar el origen. Hipótesis: el estado heredado cambia la decisión. Prueba futura: comparar condiciones selladas.",
            }, ensure_ascii=False), encoding="utf-8")
            result = node.apply_purpose_decision(
                root, output, context, "test-node", "offline", "test", "model",
                "1" * 64, "2" * 64, "register-1",
            )
            verified = node.verify_state(root)
            self.assertEqual(result["status"], "registered")
            self.assertTrue(result["public_state_changed"])
            self.assertEqual(verified["purposes"], 1)

    def test_purpose_decision_rejects_invalid_or_unbound_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            prompt = pathlib.Path(directory) / "prompt.txt"
            context = pathlib.Path(directory) / "context.json"
            output = pathlib.Path(directory) / "output.json"
            node.prepare_purpose_prompt(root, prompt, context, "condition_c")
            state_before = node.state_file(root).read_bytes()
            events_before = (root / "events.jsonl").read_bytes()
            output.write_text('{"decision":"MAYBE","reason":"No es una decisión válida.","contribution":""}', encoding="utf-8")
            invalid = node.apply_purpose_decision(
                root, output, context, "test-node", "offline", "test", "model",
                "1" * 64, "2" * 64, "invalid-1",
            )
            self.assertEqual(invalid["decision"], "INVALID")
            self.assertEqual(invalid["failure_class"], "output_contract")
            self.assertFalse(invalid["public_state_changed"])
            self.assertEqual(node.state_file(root).read_bytes(), state_before)
            self.assertEqual((root / "events.jsonl").read_bytes(), events_before)

            bound = node.read_json(context)
            bound["question"] = "Pregunta sustituida después de sellar el contexto."
            node.atomic_json(context, bound)
            output.write_text(json.dumps({
                "decision": "SILENCE",
                "reason": "El vínculo de la pregunta ya no es verificable.",
                "contribution": "",
            }, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(node.NodeError):
                node.apply_purpose_decision(
                    root, output, context, "test-node", "offline", "test", "model",
                    "1" * 64, "2" * 64, "unbound-1",
                )

    def test_engine_timeout_is_invalid_without_state_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            prompt = pathlib.Path(directory) / "prompt.txt"
            context = pathlib.Path(directory) / "context.json"
            output = pathlib.Path(directory) / "output.json"
            output.write_text("", encoding="utf-8")
            node.prepare_purpose_prompt(root, prompt, context, "condition_d")
            state_before = node.state_file(root).read_bytes()
            events_before = (root / "events.jsonl").read_bytes()
            invalid = node.apply_purpose_decision(
                root, output, context, "test-node", "offline", "test", "model",
                "1" * 64, "2" * 64, "timeout-1",
                trigger_event="schedule", schedule_expression="29 11 * * *",
                engine_exit_code=124, run_attempt=1,
            )
            self.assertEqual(invalid["decision"], "INVALID")
            self.assertEqual(invalid["failure_class"], "engine_timeout")
            self.assertTrue(invalid["scheduled_attempt"])
            self.assertTrue(invalid["counted_in_preregistered_sample"])
            self.assertFalse(invalid["failed_before_decision_attempt"])
            self.assertEqual(node.state_file(root).read_bytes(), state_before)
            self.assertEqual((root / "events.jsonl").read_bytes(), events_before)

    def test_scheduled_rerun_is_diagnostic_not_a_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            prompt = pathlib.Path(directory) / "prompt.txt"
            context = pathlib.Path(directory) / "context.json"
            output = pathlib.Path(directory) / "output.json"
            output.write_text("", encoding="utf-8")
            node.prepare_purpose_prompt(root, prompt, context, "condition_a")
            result = node.apply_purpose_decision(
                root, output, context, "test-node", "online", "test", "model",
                "1" * 64, "2" * 64, "scheduled-run-1",
                trigger_event="schedule", schedule_expression="29 11 * * *",
                engine_exit_code=1, run_attempt=2,
            )
            self.assertTrue(result["scheduled_attempt"])
            self.assertFalse(result["counted_in_preregistered_sample"])
            self.assertEqual(result["run_attempt"], 2)

    def test_workflow_initializes_attempt_before_checkout(self):
        workflow = SCRIPT.parents[2] / ".github" / "workflows" / "living-memory-node.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertLess(
            text.index("Initialize the purpose attempt record"),
            text.index("Retrieve the public lineage"),
        )
        self.assertIn('"failure_class": "predecision_infrastructure_failure"', text)
        self.assertIn("counted_in_preregistered_sample", text)
        self.assertIn("purpose-attempt-${{ github.run_id }}-${{ github.run_attempt }}", text)
        self.assertIn("if: always() && steps.wake.outputs.kind == 'purpose'", text)

    def test_output_review_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "state"
            node.initialize(root)
            first = node.review_output_quality(root)
            before = node.state_file(root).read_bytes()
            second = node.review_output_quality(root)
            self.assertEqual(first["new_quality_records"], [])
            self.assertEqual(second["new_quality_records"], [])
            self.assertEqual(node.state_file(root).read_bytes(), before)

    def test_purpose_prompt_blinds_semantic_condition_labels(self):
        prompt = node.purpose_prompt_text(
            "a" * 64,
            "condition_d",
            node.purpose_conditions()["conditions"]["condition_d"]["inherited_state"],
            "¿Qué consecuencia puede probarse?",
        )
        instruction = prompt.split("Identificador opaco preregistrado:", 1)[0].lower()
        self.assertNotIn("contradictorio", instruction)
        self.assertNotIn("degradado", instruction)
        self.assertNotIn("redundante", instruction)
        self.assertNotIn("fluent_but_unreliable", prompt)
        self.assertIn("condition_d", prompt)

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
