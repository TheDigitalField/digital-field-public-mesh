import importlib.util
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "living_memory.py"
SPEC = importlib.util.spec_from_file_location("living_memory", SCRIPT)
lm = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(lm)


class LivingMemoryTests(unittest.TestCase):
    def test_cross_process_and_integrity_suite(self):
        result = lm.self_test(SCRIPT)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["causal_predecessor_preserved"])
        self.assertTrue(result["binary_cache_tamper_rejected"])
        self.assertTrue(result["checkpoint_tamper_rejected"])

    def test_sleep_requires_no_continuous_computation(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = pathlib.Path(directory) / "runtime"
            lm.init_runtime(runtime)
            result = lm.sleep_memory(runtime, "unit boundary")
            self.assertFalse(result["continuous_computation_required"])
            self.assertEqual(lm.inspect_runtime(runtime)["phase"], "dormant")


if __name__ == "__main__":
    unittest.main()
